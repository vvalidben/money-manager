"""Recurring entries: schedules that record income or expenses by themselves.

``record_due`` records every date that has come (start-up, then hourly while
the app is open). Each transaction and the schedule's move to its next date
are written in one unit of work, so a date is never recorded twice; a date
that cannot be recorded (e.g. the category was archived) is reported and
tried again next time. Every transaction goes through ``TransactionService``,
so all the usual rules apply.
"""

# Deferred annotations: the ``list`` method would otherwise shadow the built-in.
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy.orm import Session

from money_manager.core.errors import NotFoundError, ValidationError
from money_manager.domain.entities import TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.money import DEFAULT_CURRENCY, AmountInput, Money
from money_manager.domain.recurring import (
    FUTURE_LIMIT_YEARS,
    MAX_CATCH_UP,
    PAST_LIMIT_DAYS,
    RECURRING_TYPES,
    RecordOutcome,
    RecordProblem,
    RecurringEntry,
)
from money_manager.domain.subscriptions import Frequency, advance
from money_manager.domain.validation import (
    MAX_DESCRIPTION_LENGTH,
    clean_name,
    positive_amount,
    validate_id,
)
from money_manager.persistence.database import Database
from money_manager.persistence.models import RecurringEntryModel
from money_manager.persistence.repositories import (
    AccountRepository,
    CategoryRepository,
    RecurringRepository,
)
from money_manager.services.transaction_service import TransactionService
from money_manager.core.i18n import tr

logger = logging.getLogger(__name__)

RECURRING_NOTE = "Recorded automatically (recurring)"


@dataclass(frozen=True, slots=True)
class _Valid:
    description: str
    type: TransactionType
    amount: Money
    account_id: int
    category_id: int
    frequency: Frequency
    first_date: date


class RecurringService:
    def __init__(self, database: Database, transactions: TransactionService, *,
                 today: Callable[[], date] = date.today,
                 base_currency: str = DEFAULT_CURRENCY) -> None:
        self._database = database
        self._transactions = transactions
        self._today = today
        self._currency = base_currency

    # --------------------------------------------------------------- queries

    def list(self) -> list[RecurringEntry]:
        """Every schedule, next date first."""
        with self._database.session() as session:
            return [self._to_domain(m) for m in RecurringRepository(session).list()]

    def get(self, entry_id: int) -> RecurringEntry:
        with self._database.session() as session:
            return self._to_domain(self._require(session, entry_id))

    # ------------------------------------------------------------- changes

    def create(self, description: str, *, type: TransactionType | str, amount: AmountInput,
               account_id: int, category_id: int, frequency: Frequency | str,
               first_date: date) -> RecurringEntry:
        """A new schedule; dates already past are recorded by the next ``record_due``."""
        with self._database.session() as session:
            valid = self._validate(session, description, type, amount, account_id,
                                   category_id, frequency, first_date)
            model = RecurringRepository(session).add(RecurringEntryModel(
                description=valid.description, type=valid.type.value,
                amount_minor=valid.amount.minor_units, account_id=valid.account_id,
                category_id=valid.category_id, frequency=valid.frequency.value,
                next_date=valid.first_date, anchor_day=valid.first_date.day, is_active=True))
            entry = self._to_domain(model)
        logger.info("Created recurring entry %s", entry.id)
        return entry

    def update(self, entry_id: int, description: str, *, type: TransactionType | str,
               amount: AmountInput, account_id: int, category_id: int,
               frequency: Frequency | str, next_date: date) -> RecurringEntry:
        """Change a schedule; already recorded transactions stay as they are."""
        with self._database.session() as session:
            model = self._require(session, entry_id)
            valid = self._validate(session, description, type, amount, account_id,
                                   category_id, frequency, next_date,
                                   keep_category_id=model.category_id)
            model.description = valid.description
            model.type = valid.type.value
            model.amount_minor = valid.amount.minor_units
            model.account_id = valid.account_id
            model.category_id = valid.category_id
            model.frequency = valid.frequency.value
            if valid.first_date != model.next_date:
                model.next_date = valid.first_date
                model.anchor_day = valid.first_date.day
            session.flush()
            entry = self._to_domain(model)
        logger.info("Updated recurring entry %s", entry.id)
        return entry

    def set_active(self, entry_id: int, active: bool) -> RecurringEntry:
        """Pause or resume. Resuming does not record the dates missed while paused."""
        with self._database.session() as session:
            model = self._require(session, entry_id)
            if active and not model.is_active:
                today = self._today()
                anchor = model.anchor_day
                frequency = Frequency(model.frequency)
                while model.next_date < today:  # dates missed while paused are skipped
                    model.next_date = advance(model.next_date, frequency, anchor)
            model.is_active = bool(active)
            session.flush()
            entry = self._to_domain(model)
        logger.info("Recurring entry %s %s", entry_id, "resumed" if active else "paused")
        return entry

    def delete(self, entry_id: int) -> None:
        """Delete the schedule; transactions it recorded are kept."""
        with self._database.session() as session:
            RecurringRepository(session).delete(self._require(session, entry_id))
        logger.info("Deleted recurring entry %s", entry_id)

    def record_due(self) -> RecordOutcome:
        """Record every date up to today of every active schedule."""
        today = self._today()
        recorded = 0
        problems: list[RecordProblem] = []
        with self._database.session() as session:
            entries = list(RecurringRepository(session).due(today))
        for model_id in (m.id for m in entries):
            count, problem = self._record_entry(model_id, today)
            recorded += count
            if problem is not None:
                problems.append(problem)
        if recorded or problems:
            logger.info("Recorded %d recurring entries (%d problems)", recorded, len(problems))
        return RecordOutcome(recorded, tuple(problems))

    def _record_entry(self, entry_id: int, today: date) -> tuple[int, RecordProblem | None]:
        count = 0
        for _ in range(MAX_CATCH_UP):
            with self._database.session() as session:  # one date per unit of work
                model = RecurringRepository(session).get(entry_id)
                if model is None or not model.is_active or model.next_date > today:
                    return count, None
                due = model.next_date
                draft = TransactionDraft(model.account_id, TransactionType(model.type),
                                         Money.from_minor_units(model.amount_minor,
                                                                self._currency).amount,
                                         due, model.category_id,
                                         description=model.description, notes=tr(RECURRING_NOTE))
                try:
                    self._transactions.create_in_session(session, draft)
                except ValidationError as exc:  # raised before anything is added
                    return count, RecordProblem(entry_id, model.description, due, str(exc))
                model.next_date = advance(due, Frequency(model.frequency), model.anchor_day)
                session.flush()
            count += 1
        return count, None

    # -------------------------------------------------------------- helpers

    def _validate(self, session: Session, description: object, type_: object, amount: object,
                  account_id: object, category_id: object, frequency: object,
                  first_date: object, *, keep_category_id: int | None = None) -> _Valid:
        text = clean_name(description, field="description", max_length=MAX_DESCRIPTION_LENGTH)
        try:
            kind = TransactionType(type_)
        except ValueError:
            kind = None
        if kind not in RECURRING_TYPES:
            raise ValidationError(tr("Choose income or expense."), "type")
        assert kind is not None
        try:
            clean_frequency = Frequency(frequency)
        except ValueError:
            raise ValidationError(tr("Choose how often it repeats."), "frequency") from None
        if isinstance(first_date, datetime) or not isinstance(first_date, date):
            raise ValidationError(tr("Enter a valid calendar date."), "first_date")
        today = self._today()
        if (today - first_date).days > PAST_LIMIT_DAYS:
            raise ValidationError(tr("The first date cannot be more than a year ago."), "first_date")
        if first_date.year > today.year + FUTURE_LIMIT_YEARS:
            raise ValidationError(tr("The first date must be within {0} years.", FUTURE_LIMIT_YEARS),
                                  "first_date")
        account = AccountRepository(session).get(validate_id(account_id, "account_id"))
        if account is None:
            raise ValidationError(tr("Choose an account."), "account_id")
        if first_date < account.opening_date:
            raise ValidationError(
                tr("The first date cannot be before the account was opened ({0}).", account.opening_date.isoformat()), "first_date")
        category = CategoryRepository(session).get(validate_id(category_id, "category_id"))
        if category is None:
            raise ValidationError(tr("Choose a category."), "category_id")
        wanted = CategoryKind.INCOME if kind is TransactionType.INCOME else CategoryKind.EXPENSE
        if category.kind != wanted.value:
            raise ValidationError(tr("'{0}' is not an {1} category.", category.name, tr(wanted.value)),
                                  "category_id")
        if category.is_archived and category.id != keep_category_id:
            raise ValidationError(tr("The category '{0}' is archived.", category.name), "category_id")
        return _Valid(text, kind, Money(positive_amount(amount), self._currency), account.id,
                      category.id, clean_frequency, first_date)

    @staticmethod
    def _require(session: Session, entry_id: int) -> RecurringEntryModel:
        model = RecurringRepository(session).get(validate_id(entry_id, "entry_id"))
        if model is None:
            raise NotFoundError(tr("Recurring entry {0!r} does not exist.", entry_id))
        return model

    def _to_domain(self, model: RecurringEntryModel) -> RecurringEntry:
        return RecurringEntry(
            id=model.id, description=model.description, type=TransactionType(model.type),
            amount=Money.from_minor_units(model.amount_minor, self._currency),
            account_id=model.account_id, category_id=model.category_id,
            frequency=Frequency(model.frequency), next_date=model.next_date,
            anchor_day=model.anchor_day, is_active=model.is_active)

