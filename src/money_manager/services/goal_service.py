"""Financial goals.

Two ways to track a goal:

* **Allocation-backed (recommended):** the goal is linked to an allocation and
  its current amount *is* that allocation's balance (derived, never stored).
  Adding money is a transfer from Available into the allocation; withdrawing
  is a transfer back. Transfers never change the real balance (Sprint 3), an
  allocation can back only one goal, and spending tagged to the allocation
  reduces the goal — so goal money is never counted twice.
* **Manual:** for money held outside the app. The current amount is a number
  the user updates; it is not part of any balance, allocation or statistic.

Every public method runs in one database transaction.
"""

import logging
from collections.abc import Callable
from datetime import date

from sqlalchemy.orm import Session

from money_manager.core.errors import ConflictError, NotFoundError, ValidationError
from money_manager.domain.goals import GoalProgress, GoalsSummary, order_goals
from money_manager.domain.money import DEFAULT_CURRENCY, AmountInput, Money
from money_manager.domain.validation import (
    ValidGoal,
    is_record_id,
    non_negative_amount,
    normalize_name,
    positive_amount,
    validate_allocation_name,
    validate_goal,
    validate_id,
)
from money_manager.persistence.database import Database
from money_manager.persistence.mappers import goal_to_domain
from money_manager.persistence.models import GoalModel
from money_manager.persistence.repositories import AllocationRepository, GoalRepository
from money_manager.services.allocation_service import (
    archive_allocation_in_session,
    create_allocation_in_session,
)
from money_manager.services.allocation_transfer_service import transfer_in_session
from money_manager.core.i18n import tr

logger = logging.getLogger(__name__)

CONTRIBUTION_NOTE = "Goal contribution: {name}"
WITHDRAWAL_NOTE = "Goal withdrawal: {name}"


class GoalService:
    def __init__(
        self,
        database: Database,
        *,
        today: Callable[[], date] = date.today,
        base_currency: str = DEFAULT_CURRENCY,
    ) -> None:
        self._database = database
        self._today = today
        self._currency = base_currency

    # --------------------------------------------------------------- queries

    def list(self) -> list[GoalProgress]:
        """Every goal with its progress, unfinished goals first."""
        with self._database.session() as session:
            return list(order_goals(goal_progress_in_session(session, self._currency, self._today())))

    def summary(self) -> GoalsSummary:
        return GoalsSummary(tuple(self.list()), self._currency)

    def get(self, goal_id: int) -> GoalProgress:
        with self._database.session() as session:
            model = _require(GoalRepository(session), goal_id)
            return _progress(session, model, self._currency, self._today())

    # -------------------------------------------------------------- creation

    def create_with_new_allocation(
        self,
        name: str,
        *,
        target: AmountInput,
        deadline: date | None = None,
        description: str = "",
        initial_amount: AmountInput = 0,
    ) -> GoalProgress:
        """Create the goal and an allocation of the same name holding its money.

        ``initial_amount`` is moved from Available in the same transaction.
        """
        valid = self._validate(name, target, deadline, description)
        allocation_name = validate_allocation_name(valid.name)
        funding = Money(non_negative_amount(initial_amount, "initial_amount"), self._currency)
        today = self._today()
        with self._database.session() as session:
            self._ensure_name_available(session, valid.name)
            allocation = create_allocation_in_session(session, allocation_name, funding, today)
            model = self._add(session, valid, allocation_id=allocation.id, manual_minor=None)
            progress = _progress(session, model, self._currency, today)
        logger.info("Created goal %s backed by new allocation %s", model.id, allocation.id)
        return progress

    def create_with_allocation(
        self,
        name: str,
        *,
        target: AmountInput,
        allocation_id: int,
        deadline: date | None = None,
        description: str = "",
    ) -> GoalProgress:
        """Create a goal backed by an existing allocation (and the money already in it)."""
        valid = self._validate(name, target, deadline, description)
        today = self._today()
        with self._database.session() as session:
            self._ensure_name_available(session, valid.name)
            allocation = AllocationRepository(session).get(validate_id(allocation_id, "allocation_id"))
            if allocation is None:
                raise ValidationError(tr("The selected allocation does not exist."), "allocation_id")
            if allocation.is_archived:
                raise ValidationError(
                    tr("The allocation '{0}' is archived.", allocation.name), "allocation_id"
                )
            linked = GoalRepository(session).get_by_allocation(allocation.id)
            if linked is not None:
                raise ConflictError(
                    tr("The allocation '{0}' already holds the money for the goal '{1}'. Money "
                       "can count towards only one goal.", allocation.name, linked.name)
                )
            model = self._add(session, valid, allocation_id=allocation.id, manual_minor=None)
            progress = _progress(session, model, self._currency, today)
        logger.info("Created goal %s backed by allocation %s", model.id, allocation_id)
        return progress

    def create_manual(
        self,
        name: str,
        *,
        target: AmountInput,
        current: AmountInput = 0,
        deadline: date | None = None,
        description: str = "",
    ) -> GoalProgress:
        """Create a goal whose progress the user records by hand."""
        valid = self._validate(name, target, deadline, description)
        current_money = Money(non_negative_amount(current, "current"), self._currency)
        with self._database.session() as session:
            self._ensure_name_available(session, valid.name)
            model = self._add(session, valid, allocation_id=None,
                              manual_minor=current_money.minor_units)
            progress = _progress(session, model, self._currency, self._today())
        logger.info("Created manual goal %s", model.id)
        return progress

    # ---------------------------------------------------------------- update

    def update(
        self,
        goal_id: int,
        *,
        name: str,
        target: AmountInput,
        deadline: date | None,
        description: str,
    ) -> GoalProgress:
        """Change name, target, deadline and description (the tracking mode stays)."""
        with self._database.session() as session:
            repository = GoalRepository(session)
            model = _require(repository, goal_id)
            valid = self._validate(name, target, deadline, description,
                                   current_deadline=model.deadline)
            self._ensure_name_available(session, valid.name, exclude_id=model.id)
            model.name = valid.name
            model.normalized_name = normalize_name(valid.name)
            model.target_minor = valid.target.minor_units
            model.deadline = valid.deadline
            model.description = valid.description
            session.flush()
            progress = _progress(session, model, self._currency, self._today())
        logger.info("Updated goal %s", goal_id)
        return progress

    def set_manual_amount(self, goal_id: int, amount: AmountInput) -> GoalProgress:
        """Record how much has been saved for a manually tracked goal."""
        value = Money(non_negative_amount(amount), self._currency)
        with self._database.session() as session:
            model = _require(GoalRepository(session), goal_id)
            if model.allocation_id is not None:
                raise ValidationError(
                    tr("This goal's progress is the balance of its allocation; add or withdraw "
                    "money instead."),
                    "amount",
                )
            model.manual_current_minor = value.minor_units
            session.flush()
            progress = _progress(session, model, self._currency, self._today())
        logger.info("Updated the manual amount of goal %s", goal_id)
        return progress

    def contribute(self, goal_id: int, amount: AmountInput) -> GoalProgress:
        """Add money: a transfer from Available (backed goals) or a higher manual amount."""
        return self._move(goal_id, amount, into_goal=True)

    def withdraw(self, goal_id: int, amount: AmountInput) -> GoalProgress:
        """Take money back: a transfer to Available (backed goals) or a lower manual amount."""
        return self._move(goal_id, amount, into_goal=False)

    # ---------------------------------------------------------------- delete

    def delete(self, goal_id: int, *, release_money: bool = False) -> None:
        """Delete a goal. Money is never deleted with it.

        For an allocation-backed goal the allocation (and its money) stays as it
        is, unless ``release_money`` is set: then the allocation is archived and
        its balance returns to Available, all in the same transaction.
        """
        with self._database.session() as session:
            repository = GoalRepository(session)
            model = _require(repository, goal_id)
            allocation_id = model.allocation_id
            repository.delete(model)
            if release_money and allocation_id is not None:
                allocation = AllocationRepository(session).get(allocation_id)
                if allocation is not None:
                    archive_allocation_in_session(session, allocation, self._currency,
                                                  self._today())
        logger.info("Deleted goal %s (money released: %s)", goal_id, release_money)

    # --------------------------------------------------------------- helpers

    def _move(self, goal_id: int, amount: AmountInput, *, into_goal: bool) -> GoalProgress:
        value = Money(positive_amount(amount), self._currency)
        today = self._today()
        with self._database.session() as session:
            model = _require(GoalRepository(session), goal_id)
            if model.allocation_id is None:
                assert model.manual_current_minor is not None
                change = value.minor_units if into_goal else -value.minor_units
                new_minor = model.manual_current_minor + change
                if new_minor < 0:
                    raise ValidationError(
                        tr("You cannot withdraw more than the goal's recorded amount."), "amount"
                    )
                model.manual_current_minor = new_minor
                session.flush()
            else:
                note = tr(CONTRIBUTION_NOTE if into_goal else WITHDRAWAL_NOTE).format(
                    name=model.name)
                transfer_in_session(
                    session,
                    from_allocation_id=None if into_goal else model.allocation_id,
                    to_allocation_id=model.allocation_id if into_goal else None,
                    amount=value.amount,
                    on=today,
                    note=note,
                    currency=self._currency,
                    today=today,
                )
            progress = _progress(session, model, self._currency, today)
        logger.info("%s goal %s", "Contributed to" if into_goal else "Withdrew from", goal_id)
        return progress

    def _validate(
        self,
        name: str,
        target: AmountInput,
        deadline: date | None,
        description: str,
        *,
        current_deadline: date | None = None,
    ) -> ValidGoal:
        return validate_goal(
            name=name,
            target=target,
            deadline=deadline,
            description=description,
            currency=self._currency,
            today=self._today(),
            current_deadline=current_deadline,
        )

    def _add(
        self, session: Session, valid: ValidGoal, *, allocation_id: int | None,
        manual_minor: int | None,
    ) -> GoalModel:
        return GoalRepository(session).add(
            GoalModel(
                name=valid.name,
                normalized_name=normalize_name(valid.name),
                description=valid.description,
                target_minor=valid.target.minor_units,
                start_date=self._today(),
                deadline=valid.deadline,
                allocation_id=allocation_id,
                manual_current_minor=manual_minor,
            )
        )

    @staticmethod
    def _ensure_name_available(session: Session, name: str, exclude_id: int | None = None) -> None:
        existing = GoalRepository(session).get_by_normalized_name(normalize_name(name))
        if existing is not None and existing.id != exclude_id:
            raise ConflictError(tr("A goal named '{0}' already exists.", existing.name))


def goal_progress_in_session(session: Session, currency: str, today: date) -> list[GoalProgress]:
    """Progress of every goal, from one goal query and one balance aggregate."""
    models = GoalRepository(session).list_all()
    if not models:
        return []
    balances = AllocationRepository(session).balances_minor()
    names = {a.id: a.name for a in AllocationRepository(session).list(include_archived=True)}
    return [build_goal_progress(model, balances, names, currency, today) for model in models]


def _progress(session: Session, model: GoalModel, currency: str, today: date) -> GoalProgress:
    balances = AllocationRepository(session).balances_minor() if model.allocation_id else {}
    allocation = (
        AllocationRepository(session).get(model.allocation_id) if model.allocation_id else None
    )
    names = {allocation.id: allocation.name} if allocation is not None else {}
    return build_goal_progress(model, balances, names, currency, today)


def build_goal_progress(
    model: GoalModel, balances: dict[int, int], allocation_names: dict[int, str], currency: str,
    today: date,
) -> GoalProgress:
    goal = goal_to_domain(model, currency)
    if goal.allocation_id is None:
        assert goal.manual_amount is not None
        current = goal.manual_amount
    else:
        current = Money.from_minor_units(balances.get(goal.allocation_id, 0), currency)
    return GoalProgress(
        goal=goal,
        current=current,
        today=today,
        allocation_name=allocation_names.get(goal.allocation_id) if goal.allocation_id else None,
    )


def _require(repository: GoalRepository, goal_id: int) -> GoalModel:
    model = repository.get(goal_id) if is_record_id(goal_id) else None
    if model is None:
        raise NotFoundError(tr("Goal {0!r} does not exist.", goal_id))
    return model
