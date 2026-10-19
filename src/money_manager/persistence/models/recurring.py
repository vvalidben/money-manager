from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from money_manager.domain.recurring import RECURRING_TYPES
from money_manager.domain.subscriptions import Frequency
from money_manager.domain.validation import MAX_DESCRIPTION_LENGTH
from money_manager.persistence.base import Base, TimestampMixin, in_values


class RecurringEntryModel(TimestampMixin, Base):
    """A schedule that records an income or expense by itself on each date."""

    __tablename__ = "recurring_entries"
    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="amount_positive"),
        CheckConstraint(in_values("type", list(RECURRING_TYPES)), name="valid_type"),
        CheckConstraint(in_values("frequency", Frequency), name="valid_frequency"),
        CheckConstraint("anchor_day BETWEEN 1 AND 31", name="valid_anchor_day"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    description: Mapped[str] = mapped_column(String(MAX_DESCRIPTION_LENGTH))
    type: Mapped[str] = mapped_column(String(16))
    amount_minor: Mapped[int]
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"),
                                            index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"))
    frequency: Mapped[str] = mapped_column(String(16))
    next_date: Mapped[date] = mapped_column(Date)
    anchor_day: Mapped[int]
    is_active: Mapped[bool] = mapped_column(default=True)
