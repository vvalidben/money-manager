"""Investment tracking: holdings, contributions, withdrawals and valuations.

No market data, no automatic prices, no recommendations — values are what the
user enters. See ``domain.investments`` for how returns are (and are not)
calculated.

Money flow
----------
* A contribution **paid from one of the user's accounts** creates one real
  expense in an *investment* category (so the Sprint 6 investment rate counts
  it), optionally paid from an allocation. The contribution reads its amount
  and date from that transaction; deleting the transaction deletes it.
* An **external** contribution or a withdrawal never touches the balance.
* Net worth = account balance + known investment values. Money sent to an
  investment has already left the balance as an expense, so nothing is
  counted twice.
"""

# Deferred annotations: the ``list`` method would otherwise shadow the built-in.
from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable, Sequence
from datetime import date

from sqlalchemy.orm import Session

from money_manager.core.errors import ConflictError, NotFoundError, ValidationError
from money_manager.domain.entities import TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.investments import (
    EntryKind,
    InvestmentEntry,
    InvestmentKind,
    InvestmentPosition,
    PortfolioSummary,
    Valuation,
)
from money_manager.domain.money import DEFAULT_CURRENCY, AmountInput, Money
from money_manager.domain.validation import (
    MAX_INVESTMENT_NOTE_LENGTH,
    clean_text,
    is_record_id,
    non_negative_amount,
    normalize_name,
    positive_amount,
    validate_date,
    validate_id,
    validate_investment,
)
from money_manager.persistence.database import Database
from money_manager.persistence.mappers import (
    investment_entry_to_domain,
    investment_to_domain,
    valuation_to_domain,
)
from money_manager.persistence.models import (
    InvestmentEntryModel,
    InvestmentModel,
    InvestmentValuationModel,
)
from money_manager.persistence.repositories import CategoryRepository, InvestmentRepository
from money_manager.domain.debts import debt_summary
from money_manager.services.allocation_ledger import AllocationLedger
from money_manager.services.debt_service import load_debts
from money_manager.services.transaction_service import TransactionService
from money_manager.core.i18n import tr

logger = logging.getLogger(__name__)

CONTRIBUTION_NOTE = "Investment contribution"


class InvestmentService:
    def __init__(
        self,
        database: Database,
        transactions: TransactionService,
        *,
        today: Callable[[], date] = date.today,
        base_currency: str = DEFAULT_CURRENCY,
    ) -> None:
        self._database = database
        self._transactions = transactions
        self._today = today
        self._currency = base_currency

    # --------------------------------------------------------------- queries

    def get(self, investment_id: int) -> InvestmentPosition:
        with self._database.session() as session:
            model = self._require(session, investment_id)
            return self._positions(session, [model])[0]

    def list(self, *, include_archived: bool = False) -> list[InvestmentPosition]:
        with self._database.session() as session:
            models = InvestmentRepository(session).list_all(include_archived)
            return self._positions(session, models)

    def summary(self) -> PortfolioSummary:
        """Active investments with totals, returns and net worth."""
        with self._database.session() as session:
            models = InvestmentRepository(session).list_all(include_archived=False)
            positions = self._positions(session, models)
            balance = AllocationLedger(session, self._currency).total_balance()
            debts = debt_summary(load_debts(session, self._currency), self._currency).net
        return PortfolioSummary(tuple(positions), balance, self._currency, debts)

    # ------------------------------------------------------------ investments

    def create(self, name: str, kind: InvestmentKind | str, notes: str = "") -> InvestmentPosition:
        valid = validate_investment(name=name, kind=kind, notes=notes)
        with self._database.session() as session:
            self._ensure_name_available(session, valid.name)
            model = InvestmentRepository(session).add(
                InvestmentModel(name=valid.name, normalized_name=normalize_name(valid.name),
                                kind=valid.kind.value, notes=valid.notes, is_archived=False)
            )
            position = self._positions(session, [model])[0]
        logger.info("Created investment %s", model.id)
        return position

    def update(self, investment_id: int, *, name: str, kind: InvestmentKind | str,
               notes: str) -> InvestmentPosition:
        valid = validate_investment(name=name, kind=kind, notes=notes)
        with self._database.session() as session:
            model = self._require(session, investment_id)
            self._ensure_name_available(session, valid.name, exclude_id=model.id)
            model.name = valid.name
            model.normalized_name = normalize_name(valid.name)
            model.kind = valid.kind.value
            model.notes = valid.notes
            session.flush()
            position = self._positions(session, [model])[0]
        logger.info("Updated investment %s", investment_id)
        return position

    def set_archived(self, investment_id: int, archived: bool) -> InvestmentPosition:
        """Archive a closed position: it leaves the portfolio totals but keeps its history."""
        if not isinstance(archived, bool):
            raise ValidationError(tr("Choose archived or active."), "is_archived")
        with self._database.session() as session:
            model = self._require(session, investment_id)
            model.is_archived = archived
            session.flush()
            return self._positions(session, [model])[0]

    def delete(self, investment_id: int) -> None:
        """Delete the investment and its history.

        Expenses recorded for its contributions are real money movements and
        stay in the transactions (as spending in an investment category).
        """
        with self._database.session() as session:
            InvestmentRepository(session).delete(self._require(session, investment_id))
        logger.info("Deleted investment %s", investment_id)

    # ---------------------------------------------------------------- entries

    def add_contribution(
        self,
        investment_id: int,
        amount: AmountInput,
        on: date,
        *,
        note: str = "",
        account_id: int | None = None,
        category_id: int | None = None,
        allocation_id: int | None = None,
    ) -> InvestmentEntry:
        """Record money put into an investment.

        With ``account_id`` the money left one of the user's accounts: one
        expense is created in ``category_id`` (an investment category) and the
        contribution is linked to it. Without it the contribution is external.
        """
        clean_note = clean_text(note, field="note", max_length=MAX_INVESTMENT_NOTE_LENGTH)
        with self._database.session() as session:
            model = self._require_active(session, investment_id)
            if account_id is None:
                entry = self._add_external(session, model, EntryKind.CONTRIBUTION, amount, on,
                                           clean_note)
            else:
                positive_amount(amount)  # the plain message, before any transaction rule
                self._require_investment_category(session, category_id)
                transaction = self._transactions.create_in_session(
                    session,
                    TransactionDraft(
                        account_id=account_id,
                        type=TransactionType.EXPENSE,
                        amount=amount,
                        occurred_on=on,
                        category_id=category_id,
                        description=model.name,
                        notes=clean_note or tr(CONTRIBUTION_NOTE),
                        allocation_id=allocation_id,
                    ),
                )
                entry_model = InvestmentRepository(session).add_entry(
                    InvestmentEntryModel(investment_id=model.id, kind=EntryKind.CONTRIBUTION.value,
                                         transaction_id=transaction.id, note=clean_note)
                )
                entry = investment_entry_to_domain(entry_model, transaction.amount.minor_units,
                                                   transaction.occurred_on, self._currency)
        logger.info("Recorded a contribution to investment %s", investment_id)
        return entry

    def add_withdrawal(self, investment_id: int, amount: AmountInput, on: date, *,
                       note: str = "") -> InvestmentEntry:
        """Record money taken out (e.g. a sale). It does not touch the balance: if the
        money came back to an account, record that as a transaction too."""
        clean_note = clean_text(note, field="note", max_length=MAX_INVESTMENT_NOTE_LENGTH)
        with self._database.session() as session:
            model = self._require_active(session, investment_id)
            entry = self._add_external(session, model, EntryKind.WITHDRAWAL, amount, on, clean_note)
        logger.info("Recorded a withdrawal from investment %s", investment_id)
        return entry

    def delete_entry(self, entry_id: int) -> None:
        """Delete a contribution/withdrawal. A linked contribution is deleted together
        with its expense (they are the same money movement)."""
        with self._database.session() as session:
            repository = InvestmentRepository(session)
            entry = repository.get_entry(entry_id) if is_record_id(entry_id) else None
            if entry is None:
                raise NotFoundError(tr("Entry {0!r} does not exist.", entry_id))
            transaction_id = entry.transaction_id
            if transaction_id is None:
                repository.delete_entry(entry)
        if transaction_id is not None:
            # Deleting the transaction removes the entry too (ON DELETE CASCADE),
            # with every transaction rule (e.g. allocation refunds) applied.
            self._transactions.delete(transaction_id)
        logger.info("Deleted investment entry %s", entry_id)

    # ------------------------------------------------------------- valuations

    def set_value(self, investment_id: int, value: AmountInput, on: date, *,
                  note: str = "") -> Valuation:
        """Record the investment's value on a date (replaces a value already entered that day)."""
        amount = Money(non_negative_amount(value, "value"), self._currency)
        day = validate_date(on, field="valued_on", today=self._today())
        clean_note = clean_text(note, field="note", max_length=MAX_INVESTMENT_NOTE_LENGTH)
        with self._database.session() as session:
            model = self._require_active(session, investment_id)
            repository = InvestmentRepository(session)
            valuation = repository.valuation_on(model.id, day)
            if valuation is None:
                valuation = repository.add_valuation(
                    InvestmentValuationModel(investment_id=model.id, valued_on=day,
                                             value_minor=amount.minor_units, note=clean_note)
                )
            else:
                valuation.value_minor = amount.minor_units
                valuation.note = clean_note
                session.flush()
            result = valuation_to_domain(valuation, self._currency)
        logger.info("Recorded a valuation of investment %s", investment_id)
        return result

    def delete_valuation(self, valuation_id: int) -> None:
        with self._database.session() as session:
            repository = InvestmentRepository(session)
            valuation = (repository.get_valuation(valuation_id)
                         if is_record_id(valuation_id) else None)
            if valuation is None:
                raise NotFoundError(tr("Valuation {0!r} does not exist.", valuation_id))
            repository.delete_valuation(valuation)

    # --------------------------------------------------------------- helpers

    def _add_external(
        self, session: Session, model: InvestmentModel, kind: EntryKind, amount: AmountInput,
        on: date, note: str,
    ) -> InvestmentEntry:
        value = Money(positive_amount(amount), self._currency)
        day = validate_date(on, field="occurred_on", today=self._today())
        entry = InvestmentRepository(session).add_entry(
            InvestmentEntryModel(investment_id=model.id, kind=kind.value,
                                 amount_minor=value.minor_units, occurred_on=day, note=note)
        )
        return investment_entry_to_domain(entry, value.minor_units, day, self._currency)

    def _positions(
        self, session: Session, models: Sequence[InvestmentModel]
    ) -> list[InvestmentPosition]:
        repository = InvestmentRepository(session)
        ids = [m.id for m in models]
        entries: defaultdict[int, list[InvestmentEntry]] = defaultdict(list)
        for entry, amount_minor, day in repository.entries(ids):
            entries[entry.investment_id].append(
                investment_entry_to_domain(entry, amount_minor, day, self._currency))
        valuations: defaultdict[int, list[Valuation]] = defaultdict(list)
        for valuation in repository.valuations(ids):
            valuations[valuation.investment_id].append(
                valuation_to_domain(valuation, self._currency))
        return [
            InvestmentPosition(investment_to_domain(m), tuple(entries[m.id]),
                               tuple(valuations[m.id]), self._currency)
            for m in models
        ]

    @staticmethod
    def _require_investment_category(session: Session, category_id: int | None) -> None:
        if category_id is None:
            raise ValidationError(tr("Choose the investment category for the expense."),
                                  "category_id")
        category = CategoryRepository(session).get(validate_id(category_id, "category_id"))
        if category is None:
            raise ValidationError(tr("The selected category does not exist."), "category_id")
        if category.kind != CategoryKind.EXPENSE.value or not category.is_investment:
            raise ValidationError(
                tr("'{0}' is not an investment category. Mark it as one (Statistics → "
                   "Investment categories) or choose another.", category.name),
                "category_id",
            )

    @staticmethod
    def _ensure_name_available(session: Session, name: str, exclude_id: int | None = None) -> None:
        existing = InvestmentRepository(session).get_by_normalized_name(normalize_name(name))
        if existing is not None and existing.id != exclude_id:
            raise ConflictError(tr("An investment named '{0}' already exists.", existing.name))

    @staticmethod
    def _require(session: Session, investment_id: int) -> InvestmentModel:
        model = (InvestmentRepository(session).get(investment_id)
                 if is_record_id(investment_id) else None)
        if model is None:
            raise NotFoundError(tr("Investment {0!r} does not exist.", investment_id))
        return model

    def _require_active(self, session: Session, investment_id: int) -> InvestmentModel:
        model = self._require(session, investment_id)
        if model.is_archived:
            raise ValidationError(tr("'{0}' is archived; restore it first.", model.name), "investment_id")
        return model
