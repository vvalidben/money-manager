from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from money_manager.persistence.base import Base, TimestampMixin


class BudgetModel(TimestampMixin, Base):
    """A monthly spending limit for one expense category (removed with its category)."""

    __tablename__ = "budgets"
    __table_args__ = (CheckConstraint("amount_minor > 0", name="amount_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), unique=True
    )
    amount_minor: Mapped[int]
