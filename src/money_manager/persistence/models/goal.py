from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from money_manager.domain.validation import MAX_GOAL_NAME_LENGTH
from money_manager.persistence.base import Base, TimestampMixin


class GoalModel(TimestampMixin, Base):
    """A savings target.

    Exactly one of ``allocation_id`` / ``manual_current_minor`` is set:
    allocation-backed goals derive their progress from the allocation's
    balance (never stored here), manual goals store a user-entered amount
    that is not part of any balance. An allocation can back only one goal,
    so the same money can never count towards two goals.
    """

    __tablename__ = "goals"
    __table_args__ = (
        CheckConstraint("target_minor > 0", name="target_positive"),
        CheckConstraint(
            "(allocation_id IS NULL) <> (manual_current_minor IS NULL)", name="one_tracking_mode"
        ),
        CheckConstraint(
            "manual_current_minor IS NULL OR manual_current_minor >= 0",
            name="manual_current_not_negative",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(MAX_GOAL_NAME_LENGTH))
    normalized_name: Mapped[str] = mapped_column(String(MAX_GOAL_NAME_LENGTH), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    target_minor: Mapped[int]
    start_date: Mapped[date] = mapped_column(Date)
    deadline: Mapped[date | None] = mapped_column(Date)
    allocation_id: Mapped[int | None] = mapped_column(
        ForeignKey("allocations.id", ondelete="RESTRICT"), unique=True
    )
    manual_current_minor: Mapped[int | None]
