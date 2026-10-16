from datetime import date

from sqlalchemy import CheckConstraint, ColumnElement, Date, ForeignKey, Index, String, Text, case
from sqlalchemy.orm import Mapped, mapped_column

from money_manager.domain.enums import TransactionType
from money_manager.domain.validation import MAX_DESCRIPTION_LENGTH
from money_manager.persistence.base import Base, TimestampMixin, in_values

# Income and expenses carry a category and may be tagged to an allocation;
# balance adjustments do neither.
_CATEGORISED_TYPES = [t for t in TransactionType if t.category_kind is not None]
_INFLOW_TYPES = [t for t in TransactionType if t.sign > 0]


class TransactionModel(TimestampMixin, Base):
    """A real movement of money into or out of an account.

    The CHECK constraints repeat the most important service-level rules so
    the database stays consistent even if a bug bypasses validation.
    """

    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="amount_positive"),
        CheckConstraint(in_values("type", TransactionType), name="valid_type"),
        CheckConstraint(
            f"({in_values('type', _CATEGORISED_TYPES)}) = (category_id IS NOT NULL)",
            name="category_matches_type",
        ),
        CheckConstraint(
            f"allocation_id IS NULL OR {in_values('type', _CATEGORISED_TYPES)}",
            name="allocation_only_for_income_expense",
        ),
        CheckConstraint("length(currency) = 3", name="currency_code"),
        Index("ix_transactions_account_date", "account_id", "occurred_on"),
        # Covering indexes for the aggregates (migration 0008): balances per account,
        # per-day ledger totals / newest-first paging, and expense records.
        Index("ix_transactions_account_totals", "account_id", "type", "occurred_on",
              "amount_minor"),
        Index("ix_transactions_day_totals", "occurred_on", "type", "category_id",
              "amount_minor"),
        Index("ix_transactions_expense_records", "type", "occurred_on", "category_id",
              "amount_minor", "description"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"))
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )
    # None means the money came from / went to Available.
    allocation_id: Mapped[int | None] = mapped_column(
        ForeignKey("allocations.id", ondelete="RESTRICT"), index=True
    )
    type: Mapped[str] = mapped_column(String(20))
    # Positive integer minor units (centimes); direction comes from ``type``.
    amount_minor: Mapped[int]
    # Always equal to the account's currency; kept so each row is self-describing.
    currency: Mapped[str] = mapped_column(String(3))
    occurred_on: Mapped[date] = mapped_column(Date)
    description: Mapped[str] = mapped_column(String(MAX_DESCRIPTION_LENGTH), default="")
    notes: Mapped[str] = mapped_column(Text, default="")


def signed_amount_minor() -> ColumnElement[int]:
    """SQL expression: +amount for inflows, −amount for outflows."""
    return case(
        (TransactionModel.type.in_([t.value for t in _INFLOW_TYPES]), TransactionModel.amount_minor),
        else_=-TransactionModel.amount_minor,
    )
