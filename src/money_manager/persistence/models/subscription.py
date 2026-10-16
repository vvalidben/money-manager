from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from money_manager.domain.subscriptions import Frequency, PaymentStatus
from money_manager.domain.validation import MAX_SUBSCRIPTION_NAME_LENGTH
from money_manager.persistence.base import Base, TimestampMixin, in_values


class SubscriptionModel(TimestampMixin, Base):
    """A recurring payment schedule. It never moves money by itself."""

    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="amount_positive"),
        CheckConstraint(in_values("frequency", Frequency), name="valid_frequency"),
        CheckConstraint("anchor_day BETWEEN 1 AND 31", name="valid_anchor_day"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(MAX_SUBSCRIPTION_NAME_LENGTH))
    normalized_name: Mapped[str] = mapped_column(
        String(MAX_SUBSCRIPTION_NAME_LENGTH), unique=True
    )
    amount_minor: Mapped[int]
    frequency: Mapped[str] = mapped_column(String(16))
    # The next payment that has not been recorded or skipped yet.
    next_payment_date: Mapped[date] = mapped_column(Date)
    # Billing day of month, so month-end schedules do not drift (31 → 28 → 31).
    anchor_day: Mapped[int]
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"))
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"))
    is_active: Mapped[bool] = mapped_column(default=True)
    notes: Mapped[str] = mapped_column(Text, default="")


class SubscriptionPaymentModel(TimestampMixin, Base):
    """One due date of a subscription, confirmed as paid (with its transaction) or skipped.

    The unique (subscription, due date) pair makes recording the same payment
    twice impossible.
    """

    __tablename__ = "subscription_payments"
    __table_args__ = (
        UniqueConstraint("subscription_id", "due_date", name="uq_subscription_payments_due"),
        CheckConstraint(in_values("status", PaymentStatus), name="valid_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"), index=True
    )
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(16))
    # The real expense created for a paid occurrence (kept even if the
    # subscription is deleted; cleared if the user deletes the transaction).
    transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL")
    )
