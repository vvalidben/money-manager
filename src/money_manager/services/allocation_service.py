"""Allocation use cases: create, rename, archive, delete, summarise, audit."""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from money_manager.core.errors import ConflictError, NotFoundError, ValidationError
from money_manager.domain.allocation import AllocationSummary
from money_manager.domain.entities import Allocation
from money_manager.domain.money import DEFAULT_CURRENCY, AmountInput, Money, parse_amount
from money_manager.domain.validation import is_record_id, normalize_name, validate_allocation_name
from money_manager.persistence.database import Database
from money_manager.persistence.mappers import allocation_to_domain
from money_manager.persistence.models import AllocationModel, AllocationTransferModel
from money_manager.persistence.repositories import (
    AllocationRepository,
    AllocationTransferRepository,
    GoalRepository,
)
from money_manager.services.allocation_ledger import AllocationLedger
from money_manager.services.balance_service import BalanceService

logger = logging.getLogger(__name__)

INITIAL_ALLOCATION_NOTE = "Initial allocation"
RELEASED_ON_ARCHIVE_NOTE = "Released when archived"


@dataclass(frozen=True, slots=True)
class ConsistencyIssue:
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class ConsistencyReport:
    summary: AllocationSummary
    issues: tuple[ConsistencyIssue, ...]

    @property
    def is_consistent(self) -> bool:
        return not self.issues


class AllocationService:
    def __init__(
        self,
        database: Database,
        balances: BalanceService,
        *,
        today: Callable[[], date] = date.today,
        base_currency: str = DEFAULT_CURRENCY,
    ) -> None:
        self._database = database
        self._balances = balances
        self._today = today
        self._currency = base_currency

    def create(self, name: str, *, initial_amount: AmountInput = 0) -> Allocation:
        """Create an allocation, optionally funding it from Available in the same step."""
        clean = validate_allocation_name(name)
        amount = parse_amount(initial_amount, "initial_amount")
        if amount < 0:
            raise ValidationError("The initial amount cannot be negative.", "initial_amount")

        with self._database.session() as session:
            model = create_allocation_in_session(
                session, clean, Money(amount, self._currency), self._today()
            )
            allocation = allocation_to_domain(model)
        logger.info("Created allocation %s", allocation.id)
        return allocation

    def get(self, allocation_id: int) -> Allocation:
        with self._database.session() as session:
            return allocation_to_domain(_require(AllocationRepository(session), allocation_id))

    def list(self, *, include_archived: bool = False) -> list[Allocation]:
        with self._database.session() as session:
            models = AllocationRepository(session).list(include_archived)
            return [allocation_to_domain(m) for m in models]

    def rename(self, allocation_id: int, name: str) -> Allocation:
        clean = validate_allocation_name(name)
        with self._database.session() as session:
            repository = AllocationRepository(session)
            model = _require(repository, allocation_id)
            _ensure_name_available(repository, clean, exclude_id=model.id)
            model.name = clean
            model.normalized_name = normalize_name(clean)
            session.flush()
            return allocation_to_domain(model)

    def balance(self, allocation_id: int) -> Money:
        with self._database.session() as session:
            _require(AllocationRepository(session), allocation_id)
            return AllocationLedger(session, self._currency).balance_of(allocation_id)

    def summary(self) -> AllocationSummary:
        """Total balance, each allocation's balance and the derived Available amount."""
        with self._database.session() as session:
            return AllocationLedger(session, self._currency).summary()

    def available(self) -> Money:
        return self.summary().available

    def archive(self, allocation_id: int) -> Allocation:
        """Return the allocation's money to Available (as a transfer) and archive it."""
        with self._database.session() as session:
            model = _require(AllocationRepository(session), allocation_id)
            _ensure_not_backing_a_goal(session, model)
            archive_allocation_in_session(session, model, self._currency, self._today())
            allocation = allocation_to_domain(model)
        logger.info("Archived allocation %s", allocation_id)
        return allocation

    def restore(self, allocation_id: int) -> Allocation:
        with self._database.session() as session:
            model = _require(AllocationRepository(session), allocation_id)
            model.is_archived = False
            session.flush()
            return allocation_to_domain(model)

    def delete(self, allocation_id: int) -> None:
        """Delete an allocation that was never used; archive used ones instead."""
        with self._database.session() as session:
            repository = AllocationRepository(session)
            model = _require(repository, allocation_id)
            _ensure_not_backing_a_goal(session, model)
            if repository.has_history(model.id):
                raise ConflictError(
                    f"The allocation '{model.name}' has transfers or transactions; "
                    "archive it instead."
                )
            repository.delete(model)
        logger.info("Deleted allocation %s", allocation_id)

    def check_consistency(self) -> ConsistencyReport:
        """Audit the allocation state against the independently computed real balance."""
        with self._database.session() as session:
            ledger = AllocationLedger(session, self._currency)
            summary = ledger.summary()
            models = AllocationRepository(session).list(include_archived=True)
            balances = ledger.balances_minor()

        issues: list[ConsistencyIssue] = []
        for model in models:
            balance = Money.from_minor_units(balances.get(model.id, 0), self._currency)
            if balance.is_negative():
                issues.append(
                    ConsistencyIssue(
                        "negative_allocation",
                        f"The allocation '{model.name}' is negative ({balance}).",
                    )
                )
            if model.is_archived and not balance.is_zero():
                issues.append(
                    ConsistencyIssue(
                        "archived_with_balance",
                        f"The archived allocation '{model.name}' still holds {balance}.",
                    )
                )

        independent_total = self._balances.total_balance()
        if independent_total != summary.total_balance:
            issues.append(
                ConsistencyIssue(
                    "total_mismatch",
                    f"Total balance mismatch: {summary.total_balance} vs {independent_total}.",
                )
            )
        if summary.is_over_allocated:
            issues.append(
                ConsistencyIssue(
                    "over_allocated",
                    f"Allocations exceed the real balance by {summary.shortfall}; move money "
                    "from an allocation back to Available.",
                )
            )
        if issues:
            logger.warning("Allocation consistency check found %d issue(s)", len(issues))
        return ConsistencyReport(summary=summary, issues=tuple(issues))


def create_allocation_in_session(
    session: Session, name: str, initial_amount: Money, today: date
) -> AllocationModel:
    """Create an allocation (``name`` already validated), funding it from Available.

    Runs inside the caller's unit of work so it can be combined atomically
    with other changes (e.g. creating a goal).
    """
    repository = AllocationRepository(session)
    _ensure_name_available(repository, name)
    model = repository.add(
        AllocationModel(name=name, normalized_name=normalize_name(name), is_archived=False)
    )
    if initial_amount.is_positive():
        AllocationLedger(session, initial_amount.currency).require_funds(None, initial_amount)
        AllocationTransferRepository(session).add(
            AllocationTransferModel(
                from_allocation_id=None,
                to_allocation_id=model.id,
                amount_minor=initial_amount.minor_units,
                occurred_on=today,
                note=INITIAL_ALLOCATION_NOTE,
            )
        )
    return model


def archive_allocation_in_session(
    session: Session, model: AllocationModel, currency: str, today: date
) -> None:
    """Return the allocation's money to Available (as a transfer) and archive it."""
    if model.is_archived:
        return
    balance = AllocationLedger(session, currency).balance_of(model.id)
    if balance.is_negative():
        raise ConflictError(
            f"The allocation '{model.name}' has a negative balance; run a consistency check."
        )
    if balance.is_positive():
        AllocationTransferRepository(session).add(
            AllocationTransferModel(
                from_allocation_id=model.id,
                to_allocation_id=None,
                amount_minor=balance.minor_units,
                occurred_on=today,
                note=RELEASED_ON_ARCHIVE_NOTE,
            )
        )
    model.is_archived = True
    session.flush()


def _ensure_not_backing_a_goal(session: Session, model: AllocationModel) -> None:
    goal = GoalRepository(session).get_by_allocation(model.id)
    if goal is not None:
        raise ConflictError(
            f"The allocation '{model.name}' holds the money for the goal '{goal.name}'; "
            "delete the goal first."
        )


def _ensure_name_available(
    repository: AllocationRepository, name: str, exclude_id: int | None = None
) -> None:
    existing = repository.get_by_normalized_name(normalize_name(name))
    if existing is not None and existing.id != exclude_id:
        raise ConflictError(f"An allocation named '{existing.name}' already exists.")


def _require(repository: AllocationRepository, allocation_id: int) -> AllocationModel:
    model = repository.get(allocation_id) if is_record_id(allocation_id) else None
    if model is None:
        raise NotFoundError(f"Allocation {allocation_id!r} does not exist.")
    return model
