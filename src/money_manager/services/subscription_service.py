"""Subscriptions: recurring payment schedules confirmed one due date at a time.

Nothing here runs in the background or creates transactions on its own. The
user confirms each due date:

* **record_payment** creates exactly one real expense (through
  ``TransactionService``, so every transaction rule applies) and moves the
  schedule to the next date;
* **skip_payment** moves the schedule on without creating a transaction.

Duplicates are impossible: only the schedule's current next date can be
confirmed, each (subscription, due date) pair can be confirmed once (also
enforced by a unique database constraint), and dates more than a week away
cannot be confirmed early.
"""

# Deferred annotations: the ``list`` method would otherwise shadow the built-in
# ``list`` in annotations further down the class.
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from money_manager.core.errors import ConflictError, NotFoundError, ValidationError
from money_manager.domain.entities import Transaction, TransactionDraft
from money_manager.domain.enums import TransactionType
from money_manager.domain.money import DEFAULT_CURRENCY, AmountInput
from money_manager.domain.subscriptions import (
    Frequency,
    PaymentStatus,
    Subscription,
    SubscriptionStats,
    UpcomingPayment,
    advance,
    subscription_stats,
    upcoming_payments,
)
from money_manager.domain.validation import (
    ValidSubscription,
    is_record_id,
    normalize_name,
    validate_id,
    validate_subscription,
)
from money_manager.persistence.database import Database
from money_manager.persistence.mappers import category_to_domain, subscription_to_domain
from money_manager.persistence.models import SubscriptionModel, SubscriptionPaymentModel
from money_manager.persistence.repositories import (
    AccountRepository,
    CategoryRepository,
    SubscriptionRepository,
)
from money_manager.services.transaction_service import TransactionService

logger = logging.getLogger(__name__)

UPCOMING_DAYS = 30
EARLY_PAYMENT_DAYS = 7


@dataclass(frozen=True, slots=True)
class SubscriptionPayment:
    id: int
    subscription_id: int
    due_date: date
    status: PaymentStatus
    transaction_id: int | None


class SubscriptionService:
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

    def get(self, subscription_id: int) -> Subscription:
        with self._database.session() as session:
            return subscription_to_domain(self._require(session, subscription_id), self._currency)

    def list(self) -> list[Subscription]:
        with self._database.session() as session:
            return [subscription_to_domain(m, self._currency)
                    for m in SubscriptionRepository(session).list_all()]

    def upcoming(self, horizon_days: int = UPCOMING_DAYS) -> tuple[UpcomingPayment, ...]:
        return upcoming_payments(self.list(), self._today(), horizon_days)

    def statistics(self, horizon_days: int = UPCOMING_DAYS) -> SubscriptionStats:
        with self._database.session() as session:
            subscriptions = [subscription_to_domain(m, self._currency)
                             for m in SubscriptionRepository(session).list_all()]
            names = {c.id: c.name for c in CategoryRepository(session).list(include_archived=True)}
        return subscription_stats(subscriptions, names, self._today(), horizon_days,
                                  self._currency)

    def payments(self, subscription_id: int) -> list[SubscriptionPayment]:
        with self._database.session() as session:
            self._require(session, subscription_id)
            return [
                SubscriptionPayment(p.id, p.subscription_id, p.due_date,
                                    PaymentStatus(p.status), p.transaction_id)
                for p in SubscriptionRepository(session).payments(subscription_id)
            ]

    # ------------------------------------------------------------------ CRUD

    def create(
        self,
        name: str,
        *,
        amount: AmountInput,
        frequency: Frequency | str,
        next_payment_date: date,
        category_id: int,
        account_id: int | None = None,
        notes: str = "",
        is_active: bool = True,
    ) -> Subscription:
        with self._database.session() as session:
            valid = self._validate(session, name, amount, frequency, next_payment_date,
                                   category_id, notes)
            self._check_account(session, account_id)
            self._ensure_name_available(session, valid.name)
            model = SubscriptionRepository(session).add(
                SubscriptionModel(
                    name=valid.name,
                    normalized_name=normalize_name(valid.name),
                    amount_minor=valid.amount.minor_units,
                    frequency=valid.frequency.value,
                    next_payment_date=valid.next_payment_date,
                    anchor_day=valid.anchor_day,
                    category_id=valid.category_id,
                    account_id=account_id,
                    is_active=_flag(is_active),
                    notes=valid.notes,
                )
            )
            subscription = subscription_to_domain(model, self._currency)
        logger.info("Created subscription %s", subscription.id)
        return subscription

    def update(
        self,
        subscription_id: int,
        *,
        name: str,
        amount: AmountInput,
        frequency: Frequency | str,
        next_payment_date: date,
        category_id: int,
        account_id: int | None,
        notes: str,
    ) -> Subscription:
        """Replace the editable fields. Changing the date resets the billing day to it."""
        with self._database.session() as session:
            model = self._require(session, subscription_id)
            valid = self._validate(session, name, amount, frequency, next_payment_date,
                                   category_id, notes, keep_archived_category_id=model.category_id)
            self._check_account(session, account_id)
            self._ensure_name_available(session, valid.name, exclude_id=model.id)
            if valid.next_payment_date != model.next_payment_date:
                model.anchor_day = valid.anchor_day
            model.name = valid.name
            model.normalized_name = normalize_name(valid.name)
            model.amount_minor = valid.amount.minor_units
            model.frequency = valid.frequency.value
            model.next_payment_date = valid.next_payment_date
            model.category_id = valid.category_id
            model.account_id = account_id
            model.notes = valid.notes
            session.flush()
            subscription = subscription_to_domain(model, self._currency)
        logger.info("Updated subscription %s", subscription_id)
        return subscription

    def set_active(self, subscription_id: int, active: bool) -> Subscription:
        """Pause or resume. Paused subscriptions are left out of totals and upcoming payments."""
        with self._database.session() as session:
            model = self._require(session, subscription_id)
            model.is_active = _flag(active)
            session.flush()
            subscription = subscription_to_domain(model, self._currency)
        logger.info("Subscription %s active: %s", subscription_id, active)
        return subscription

    def delete(self, subscription_id: int) -> None:
        """Delete the schedule. Expenses already recorded for it are real and stay."""
        with self._database.session() as session:
            repository = SubscriptionRepository(session)
            repository.delete(self._require(session, subscription_id))
        logger.info("Deleted subscription %s", subscription_id)

    # -------------------------------------------------------------- payments

    def record_payment(
        self,
        subscription_id: int,
        due_date: date,
        *,
        account_id: int | None = None,
        amount: AmountInput | None = None,
        paid_on: date | None = None,
    ) -> Transaction:
        """Confirm ``due_date`` as paid: create one expense and advance the schedule."""
        today = self._today()
        with self._database.session() as session:
            model = self._require(session, subscription_id)
            self._check_confirmable(session, model, due_date, today)
            chosen_account = account_id if account_id is not None else model.account_id
            if chosen_account is None:
                raise ValidationError("Choose the account the payment was made from.",
                                      "account_id")
            transaction = self._transactions.create_in_session(
                session,
                TransactionDraft(
                    account_id=chosen_account,
                    type=TransactionType.EXPENSE,
                    amount=subscription_to_domain(model, self._currency).amount.amount
                    if amount is None else amount,
                    occurred_on=paid_on if paid_on is not None else min(due_date, today),
                    category_id=model.category_id,
                    description=model.name,
                    notes=f"Subscription payment due {due_date.isoformat()}",
                ),
            )
            self._confirm(session, model, due_date, PaymentStatus.PAID, transaction.id)
        logger.info("Recorded payment for subscription %s due %s", subscription_id, due_date)
        return transaction

    def skip_payment(self, subscription_id: int, due_date: date) -> Subscription:
        """Confirm ``due_date`` without a transaction (e.g. already entered by hand)."""
        today = self._today()
        with self._database.session() as session:
            model = self._require(session, subscription_id)
            self._check_confirmable(session, model, due_date, today)
            self._confirm(session, model, due_date, PaymentStatus.SKIPPED, None)
            subscription = subscription_to_domain(model, self._currency)
        logger.info("Skipped payment for subscription %s due %s", subscription_id, due_date)
        return subscription

    # --------------------------------------------------------------- helpers

    def _check_confirmable(
        self, session: Session, model: SubscriptionModel, due_date: object, today: date
    ) -> None:
        if isinstance(due_date, datetime) or not isinstance(due_date, date):
            raise ValidationError("Enter a valid calendar date.", "due_date")
        if not model.is_active:
            raise ValidationError(f"'{model.name}' is paused; resume it first.", "due_date")
        if SubscriptionRepository(session).payment_for(model.id, due_date) is not None:
            raise ConflictError(
                f"The payment of '{model.name}' due {due_date.isoformat()} has already been "
                "confirmed."
            )
        if due_date != model.next_payment_date:
            raise ConflictError(
                f"The next payment of '{model.name}' to confirm is the one due "
                f"{model.next_payment_date.isoformat()}."
            )
        if due_date > today + timedelta(days=EARLY_PAYMENT_DAYS):
            raise ValidationError(
                f"This payment is not due until {due_date.isoformat()}; it can be confirmed "
                f"at most {EARLY_PAYMENT_DAYS} days early.",
                "due_date",
            )

    @staticmethod
    def _confirm(
        session: Session, model: SubscriptionModel, due_date: date, status: PaymentStatus,
        transaction_id: int | None,
    ) -> None:
        SubscriptionRepository(session).add_payment(
            SubscriptionPaymentModel(
                subscription_id=model.id,
                due_date=due_date,
                status=status.value,
                transaction_id=transaction_id,
            )
        )
        model.next_payment_date = advance(due_date, Frequency(model.frequency), model.anchor_day)
        session.flush()

    def _validate(
        self,
        session: Session,
        name: str,
        amount: AmountInput,
        frequency: Frequency | str,
        next_payment_date: date,
        category_id: int,
        notes: str,
        keep_archived_category_id: int | None = None,
    ) -> ValidSubscription:
        category_model = CategoryRepository(session).get(validate_id(category_id, "category_id"))
        if category_model is None:
            raise ValidationError("The selected category does not exist.", "category_id")
        return validate_subscription(
            name=name,
            amount=amount,
            frequency=frequency,
            next_payment_date=next_payment_date,
            category=category_to_domain(category_model),
            notes=notes,
            currency=self._currency,
            today=self._today(),
            keep_archived_category_id=keep_archived_category_id,
        )

    @staticmethod
    def _check_account(session: Session, account_id: int | None) -> None:
        if account_id is None:
            return
        if AccountRepository(session).get(validate_id(account_id, "account_id")) is None:
            raise ValidationError("The selected account does not exist.", "account_id")

    @staticmethod
    def _ensure_name_available(session: Session, name: str, exclude_id: int | None = None) -> None:
        existing = SubscriptionRepository(session).get_by_normalized_name(normalize_name(name))
        if existing is not None and existing.id != exclude_id:
            raise ConflictError(f"A subscription named '{existing.name}' already exists.")

    @staticmethod
    def _require(session: Session, subscription_id: int) -> SubscriptionModel:
        repository = SubscriptionRepository(session)
        model = repository.get(subscription_id) if is_record_id(subscription_id) else None
        if model is None:
            raise NotFoundError(f"Subscription {subscription_id!r} does not exist.")
        return model


def _flag(value: object) -> bool:
    if not isinstance(value, bool):
        raise ValidationError("Choose active or paused.", "is_active")
    return value
