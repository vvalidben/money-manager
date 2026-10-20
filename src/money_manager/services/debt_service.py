"""Debts and loans: create them, record repayments, and total what is outstanding.

When money moves through one of your accounts (the loan paid out or received,
a repayment), it is recorded through ``TransactionService`` as a balance
adjustment — neither income nor spending — in the same unit of work as the
debt change. Deleting a repayment deletes its adjustment too; deleting a debt
keeps the adjustments already recorded (they are real money movements).
"""

# Deferred annotations: the ``list`` method would otherwise shadow the built-in.
from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable
from datetime import date, datetime

from sqlalchemy.orm import Session

from money_manager.core.errors import NotFoundError, ValidationError
from money_manager.domain.debts import (
    MAX_DEBT_NAME_LENGTH,
    Debt,
    DebtDirection,
    DebtPayment,
    DebtSummary,
    debt_summary,
)
from money_manager.domain.entities import TransactionDraft
from money_manager.domain.enums import TransactionType
from money_manager.domain.money import DEFAULT_CURRENCY, AmountInput, Money
from money_manager.domain.validation import (
    MAX_NOTES_LENGTH,
    clean_name,
    clean_text,
    positive_amount,
    validate_date,
    validate_id,
)
from money_manager.persistence.database import Database
from money_manager.persistence.models import DebtModel, DebtPaymentModel
from money_manager.persistence.repositories import DebtRepository, TransactionRepository
from money_manager.services.transaction_service import TransactionService
from money_manager.core.i18n import tr

logger = logging.getLogger(__name__)

MAX_PAYMENT_NOTE_LENGTH = 200


def load_debts(session: Session, currency: str) -> list[Debt]:
    """Every debt with its repayments (also used by the net worth)."""
    repository = DebtRepository(session)
    payments: defaultdict[int, list[DebtPayment]] = defaultdict(list)
    for model in repository.payments():
        payments[model.debt_id].append(DebtPayment(
            model.id, model.debt_id, Money.from_minor_units(model.amount_minor, currency),
            model.paid_on, model.transaction_id, model.note))
    return [Debt(m.id, m.name, DebtDirection(m.direction),
                 Money.from_minor_units(m.amount_minor, currency), m.start_date, m.due_date,
                 m.notes, tuple(payments[m.id])) for m in repository.list()]


class DebtService:
    def __init__(self, database: Database, transactions: TransactionService, *,
                 today: Callable[[], date] = date.today,
                 base_currency: str = DEFAULT_CURRENCY) -> None:
        self._database = database
        self._transactions = transactions
        self._today = today
        self._currency = base_currency

    # --------------------------------------------------------------- queries

    def list(self) -> list[Debt]:
        """Open debts first (nearest due date first), then settled ones."""
        with self._database.session() as session:
            debts = load_debts(session, self._currency)
        return sorted(debts, key=lambda d: (d.is_settled, d.due_date or date.max, d.start_date,
                                            d.id))

    def get(self, debt_id: int) -> Debt:
        debt_id = validate_id(debt_id, "debt_id")
        debt = next((d for d in self.list() if d.id == debt_id), None)
        if debt is None:
            raise NotFoundError(tr("Debt {0!r} does not exist.", debt_id))
        return debt

    def summary(self) -> DebtSummary:
        return debt_summary(self.list(), self._currency)

    # ------------------------------------------------------------- changes

    def create(self, name: str, *, direction: DebtDirection | str, amount: AmountInput,
               start_date: date, due_date: date | None = None, notes: str = "",
               account_id: int | None = None) -> Debt:
        """A new debt; with ``account_id`` the money is moved through that account."""
        today = self._today()
        clean = clean_name(name, field="name", max_length=MAX_DEBT_NAME_LENGTH)
        kind = _direction(direction)
        value = Money(positive_amount(amount), self._currency)
        start = validate_date(start_date, field="start_date", today=today)
        due = _due(due_date, start)
        text = clean_text(notes, field="notes", max_length=MAX_NOTES_LENGTH)
        with self._database.session() as session:
            transaction_id = None
            if account_id is not None:
                kind_type = (TransactionType.ADJUSTMENT_OUT if kind is DebtDirection.LENT
                             else TransactionType.ADJUSTMENT_IN)
                label = tr("Loan to {0}", clean) if kind is DebtDirection.LENT else tr("Loan from {0}", clean)
                transaction_id = self._transactions.create_in_session(session, TransactionDraft(
                    account_id, kind_type, value.amount, start, None, description=label)).id
            model = DebtModel(name=clean, direction=kind.value, amount_minor=value.minor_units,
                              start_date=start, due_date=due, notes=text,
                              transaction_id=transaction_id)
            DebtRepository(session).add(model)
            debt_id = model.id
        logger.info("Created debt %s", debt_id)
        return self.get(debt_id)

    def update(self, debt_id: int, name: str, *, due_date: date | None, notes: str) -> Debt:
        """Rename, change the due date or the notes (the amount stays as recorded)."""
        clean = clean_name(name, field="name", max_length=MAX_DEBT_NAME_LENGTH)
        text = clean_text(notes, field="notes", max_length=MAX_NOTES_LENGTH)
        with self._database.session() as session:
            model = self._require(session, debt_id)
            model.name = clean
            model.due_date = _due(due_date, model.start_date)
            model.notes = text
            session.flush()
        logger.info("Updated debt %s", debt_id)
        return self.get(debt_id)

    def record_payment(self, debt_id: int, amount: AmountInput, paid_on: date, *,
                       account_id: int | None = None, note: str = "") -> Debt:
        """A repayment (received when you lent, made when you borrowed)."""
        debt = self.get(debt_id)
        value = Money(positive_amount(amount), self._currency)
        day = validate_date(paid_on, field="paid_on", today=self._today())
        if day < debt.start_date:
            raise ValidationError(tr("A repayment cannot be dated before the debt started."),
                                  "paid_on")
        if value > debt.remaining:
            raise ValidationError(
                tr("Only {0} is left to repay.", str(debt.remaining)),
                "amount")
        text = clean_text(note, field="note", max_length=MAX_PAYMENT_NOTE_LENGTH)
        with self._database.session() as session:
            transaction_id = None
            if account_id is not None:
                lent = debt.direction is DebtDirection.LENT
                kind = TransactionType.ADJUSTMENT_IN if lent else TransactionType.ADJUSTMENT_OUT
                label = tr("Repayment from {0}", debt.name) if lent else tr("Repayment to {0}", debt.name)
                transaction_id = self._transactions.create_in_session(session, TransactionDraft(
                    account_id, kind, value.amount, day, None, description=label)).id
            DebtRepository(session).add(DebtPaymentModel(
                debt_id=debt.id, amount_minor=value.minor_units, paid_on=day, note=text,
                transaction_id=transaction_id))
        logger.info("Recorded a repayment of debt %s", debt.id)
        return self.get(debt.id)

    def delete_payment(self, payment_id: int) -> Debt:
        """Remove a repayment and the adjustment it recorded in an account."""
        with self._database.session() as session:
            repository = DebtRepository(session)
            payment = repository.get_payment(validate_id(payment_id, "payment_id"))
            if payment is None:
                raise NotFoundError(tr("Repayment {0!r} does not exist.", payment_id))
            debt_id, transaction_id = payment.debt_id, payment.transaction_id
            repository.delete(payment)
            if transaction_id is not None:
                transaction = TransactionRepository(session).get(transaction_id)
                if transaction is not None:
                    TransactionRepository(session).delete(transaction)
        logger.info("Deleted repayment %s", payment_id)
        return self.get(debt_id)

    def delete(self, debt_id: int) -> None:
        """Delete the debt and its repayments; recorded adjustments are kept."""
        with self._database.session() as session:
            DebtRepository(session).delete(self._require(session, debt_id))
        logger.info("Deleted debt %s", debt_id)

    @staticmethod
    def _require(session: Session, debt_id: int) -> DebtModel:
        model = DebtRepository(session).get(validate_id(debt_id, "debt_id"))
        if model is None:
            raise NotFoundError(tr("Debt {0!r} does not exist.", debt_id))
        return model


def _direction(value: object) -> DebtDirection:
    try:
        return DebtDirection(value)
    except ValueError:
        raise ValidationError(tr("Choose whether you lent or borrowed the money."),
                              "direction") from None


def _due(value: object, start: date) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime) or not isinstance(value, date):
        raise ValidationError(tr("Enter a valid calendar date."), "due_date")
    if value < start:
        raise ValidationError(tr("The due date cannot be before the start date."), "due_date")
    return value
