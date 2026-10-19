"""Transaction use cases (create, read, update, delete).

Interaction with allocations: a transaction without ``allocation_id`` changes
Available money. An income or expense tagged with an allocation changes that
allocation's balance instead. Every create, update and delete is checked so
that no allocation balance can become negative.
"""

import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import replace
from datetime import date, datetime

from sqlalchemy.orm import Session

from money_manager.core.errors import (
    ConflictError,
    InsufficientFundsError,
    NotFoundError,
    ValidationError,
)
from money_manager.domain.entities import (
    Allocation,
    Category,
    Transaction,
    TransactionDraft,
    TransactionFilter,
    TransactionPage,
    TransactionQuery,
)
from money_manager.domain.enums import TransactionType, parse_transaction_type
from money_manager.domain.money import DEFAULT_CURRENCY, Money
from money_manager.domain.validation import (
    MAX_RECORD_ID,
    ValidTransaction,
    is_record_id,
    validate_id,
    validate_transaction,
)
from money_manager.persistence.database import Database
from money_manager.persistence.mappers import (
    account_to_domain,
    allocation_to_domain,
    category_to_domain,
    transaction_to_domain,
)
from money_manager.persistence.models import TransactionModel
from money_manager.persistence.repositories import (
    AccountRepository,
    AccountTransferRepository,
    AllocationRepository,
    CategoryRepository,
    InvestmentRepository,
    TransactionRepository,
)

logger = logging.getLogger(__name__)

# allocation id -> change to its balance in minor units
AllocationEffects = dict[int, int]


MAX_PAGE_SIZE = 500
MAX_SEARCH_LENGTH = 100


class TransactionService:
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

    def search(self, query: TransactionQuery) -> TransactionPage:
        """One sorted page of matching transactions plus totals over all matches."""
        filters = _validate_query(query)
        with self._database.session() as session:
            repository = TransactionRepository(session)
            models = repository.search(
                filters,
                query.sort,
                descending=query.descending,
                offset=query.offset,
                limit=query.limit,
            )
            totals = repository.totals_matching(filters)
            return TransactionPage(
                items=tuple(transaction_to_domain(m) for m in models),
                total_count=repository.count(filters),
                offset=query.offset,
                limit=query.limit,
                income=Money.from_minor_units(
                    totals.get(TransactionType.INCOME, 0), self._currency
                ),
                expenses=Money.from_minor_units(
                    totals.get(TransactionType.EXPENSE, 0), self._currency
                ),
            )

    def create(self, draft: TransactionDraft) -> Transaction:
        with self._database.session() as session:
            transaction = self.create_in_session(session, draft)
        logger.info("Created transaction %s", transaction.id)
        return transaction

    def create_in_session(self, session: Session, draft: TransactionDraft) -> Transaction:
        """Create inside a caller-owned unit of work (used by other services)."""
        valid = self._validate(session, draft)
        _check_allocations(session, _effects(valid.allocation_id, valid.type, valid.amount))
        model = TransactionModel()
        _apply(model, valid)
        TransactionRepository(session).add(model)
        return transaction_to_domain(model)

    def get(self, transaction_id: int) -> Transaction:
        with self._database.session() as session:
            return transaction_to_domain(_require(TransactionRepository(session), transaction_id))

    def list(self, filters: TransactionFilter | None = None) -> list[Transaction]:
        with self._database.session() as session:
            models = TransactionRepository(session).list(filters or TransactionFilter())
            return [transaction_to_domain(m) for m in models]

    def update(self, transaction_id: int, draft: TransactionDraft) -> Transaction:
        """Replace every editable field; the draft is validated like a new one."""
        with self._database.session() as session:
            model = _require(TransactionRepository(session), transaction_id)
            old = transaction_to_domain(model)
            _check_transfer_link(session, model.id)
            _check_investment_link(session, model.id, draft)
            valid = self._validate(
                session,
                draft,
                keep_archived_category_id=old.category_id,
                keep_archived_allocation_id=old.allocation_id,
            )
            # Checked before the row changes, so current balances include the old effect.
            _check_allocations(
                session,
                _merge(
                    _effects(old.allocation_id, old.type, old.amount, reverse=True),
                    _effects(valid.allocation_id, valid.type, valid.amount),
                ),
            )
            _apply(model, valid)
            session.flush()
            transaction = transaction_to_domain(model)
        logger.info("Updated transaction %s", transaction.id)
        return transaction

    def delete(self, transaction_id: int) -> None:
        with self._database.session() as session:
            repository = TransactionRepository(session)
            model = _require(repository, transaction_id)
            old = transaction_to_domain(model)
            _check_transfer_link(session, model.id)
            _check_allocations(
                session, _effects(old.allocation_id, old.type, old.amount, reverse=True)
            )
            repository.delete(model)
        logger.info("Deleted transaction %s", transaction_id)

    def _validate(
        self,
        session: Session,
        draft: TransactionDraft,
        keep_archived_category_id: int | None = None,
        keep_archived_allocation_id: int | None = None,
    ) -> ValidTransaction:
        account_model = AccountRepository(session).get(validate_id(draft.account_id, "account_id"))
        if account_model is None:
            raise ValidationError("The selected account does not exist.", "account_id")

        category: Category | None = None
        if draft.category_id is not None:
            category_model = CategoryRepository(session).get(
                validate_id(draft.category_id, "category_id")
            )
            if category_model is None:
                raise ValidationError("The selected category does not exist.", "category_id")
            category = category_to_domain(category_model)

        allocation: Allocation | None = None
        if draft.allocation_id is not None:
            allocation_model = AllocationRepository(session).get(
                validate_id(draft.allocation_id, "allocation_id")
            )
            if allocation_model is not None:
                allocation = allocation_to_domain(allocation_model)

        return validate_transaction(
            draft,
            account=account_to_domain(account_model),
            category=category,
            today=self._today(),
            keep_archived_category_id=keep_archived_category_id,
            allocation=allocation,
            keep_archived_allocation_id=keep_archived_allocation_id,
        )


def _validate_query(query: TransactionQuery) -> TransactionFilter:
    """Check paging/date arguments and return the filters with a trimmed search."""
    if isinstance(query.limit, bool) or not isinstance(query.limit, int) or not (
        1 <= query.limit <= MAX_PAGE_SIZE
    ):
        raise ValidationError(f"Page size must be between 1 and {MAX_PAGE_SIZE}.", "limit")
    if (isinstance(query.offset, bool) or not isinstance(query.offset, int)
            or not 0 <= query.offset <= MAX_RECORD_ID):
        raise ValidationError("Offset must be between zero and the number of records.",
                              "offset")
    filters = query.filters
    for value, field in ((filters.start, "start"), (filters.end, "end")):
        if value is not None and (isinstance(value, datetime) or not isinstance(value, date)):
            raise ValidationError("Enter a valid calendar date.", field)
    if filters.start is not None and filters.end is not None and filters.start > filters.end:
        raise ValidationError("The start date must not be after the end date.", "start")
    search = filters.search.strip() if isinstance(filters.search, str) else ""
    if len(search) > MAX_SEARCH_LENGTH:
        raise ValidationError(
            f"Search text cannot be longer than {MAX_SEARCH_LENGTH} characters.", "search"
        )
    return replace(filters, search=search)


TRANSFER_SIDE_MESSAGE = (
    "This entry is one side of a transfer between your accounts. Delete the transfer to "
    "remove both sides; to change it, delete it and record it again."
)


def _check_transfer_link(session: Session, transaction_id: int) -> None:
    """Either side of an account transfer only changes together with the other."""
    if AccountTransferRepository(session).for_transaction(transaction_id) is not None:
        raise ConflictError(TRANSFER_SIDE_MESSAGE)


def _check_investment_link(session: Session, transaction_id: int, draft: TransactionDraft) -> None:
    """An expense that backs an investment contribution must stay an expense."""
    entry = InvestmentRepository(session).entry_for_transaction(transaction_id)
    if entry is not None and parse_transaction_type(draft.type) is not TransactionType.EXPENSE:
        raise ValidationError(
            "This expense is an investment contribution and must stay an expense. Delete it "
            "on the Investments page instead.",
            "type",
        )


def _effects(
    allocation_id: int | None,
    transaction_type: TransactionType,
    amount: Money,
    *,
    reverse: bool = False,
) -> AllocationEffects:
    """How a transaction changes its allocation's balance (empty if untagged)."""
    if allocation_id is None:
        return {}
    change = transaction_type.sign * amount.minor_units
    return {allocation_id: -change if reverse else change}


def _merge(*effects: AllocationEffects) -> AllocationEffects:
    merged: defaultdict[int, int] = defaultdict(int)
    for effect in effects:
        for allocation_id, change in effect.items():
            merged[allocation_id] += change
    return dict(merged)


def _check_allocations(session: Session, effects: AllocationEffects) -> None:
    """Refuse changes that would leave any allocation below zero, or that would put
    money back into an archived allocation (archiving returned its money to
    Available, so it must stay empty; e.g. deleting an old expense tagged to it)."""
    repository = AllocationRepository(session)
    for allocation_id, change in effects.items():
        if change > 0:
            model = repository.get(allocation_id)
            if model is not None and model.is_archived:
                raise ValidationError(
                    f"The allocation '{model.name}' is archived, and this change would put "
                    "money back into it. Restore the allocation first, or record the "
                    "transaction against Available.",
                    "allocation_id",
                )
    decreases = {aid: change for aid, change in effects.items() if change < 0}
    if not decreases:
        return
    balances = repository.balances_minor()
    for allocation_id, change in decreases.items():
        current = balances.get(allocation_id, 0)
        if current + change < 0:
            model = repository.get(allocation_id)
            name = model.name if model is not None else str(allocation_id)
            raise InsufficientFundsError(
                f"The allocation '{name}' holds {Money.from_minor_units(current)}; this change "
                f"would leave it at {Money.from_minor_units(current + change)}. Move money "
                "into it first, or record the transaction against Available.",
                "allocation_id",
            )


def _apply(model: TransactionModel, valid: ValidTransaction) -> None:
    model.account_id = valid.account_id
    model.type = valid.type.value
    model.amount_minor = valid.amount.minor_units
    model.currency = valid.amount.currency
    model.occurred_on = valid.occurred_on
    model.category_id = valid.category_id
    model.allocation_id = valid.allocation_id
    model.description = valid.description
    model.notes = valid.notes


def _require(repository: TransactionRepository, transaction_id: int) -> TransactionModel:
    model = repository.get(transaction_id) if is_record_id(transaction_id) else None
    if model is None:
        raise NotFoundError(f"Transaction {transaction_id!r} does not exist.")
    return model
