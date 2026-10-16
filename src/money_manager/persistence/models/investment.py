from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from money_manager.domain.investments import EntryKind, InvestmentKind
from money_manager.domain.validation import MAX_INVESTMENT_NAME_LENGTH
from money_manager.persistence.base import Base, TimestampMixin, in_values


class InvestmentModel(TimestampMixin, Base):
    """A holding outside the tracked accounts (stock, ETF, crypto, gold, …)."""

    __tablename__ = "investments"
    __table_args__ = (CheckConstraint(in_values("kind", InvestmentKind), name="valid_kind"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(MAX_INVESTMENT_NAME_LENGTH))
    normalized_name: Mapped[str] = mapped_column(String(MAX_INVESTMENT_NAME_LENGTH), unique=True)
    kind: Mapped[str] = mapped_column(String(16))
    notes: Mapped[str] = mapped_column(Text, default="")
    is_archived: Mapped[bool] = mapped_column(default=False)


class InvestmentEntryModel(TimestampMixin, Base):
    """A contribution or withdrawal.

    Either it is backed by a transaction (money left one of the user's
    accounts; amount and date are read from that transaction and are NULL
    here) or it is external and stores its own amount and date. Deleting the
    backing transaction deletes the entry, so they can never disagree.
    """

    __tablename__ = "investment_entries"
    __table_args__ = (
        CheckConstraint(in_values("kind", EntryKind), name="valid_kind"),
        CheckConstraint(
            "(transaction_id IS NULL AND amount_minor > 0 AND occurred_on IS NOT NULL) OR "
            "(transaction_id IS NOT NULL AND amount_minor IS NULL AND occurred_on IS NULL)",
            name="own_amount_or_transaction",
        ),
        CheckConstraint(
            "transaction_id IS NULL OR kind = 'contribution'",
            name="only_contributions_have_transactions",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    investment_id: Mapped[int] = mapped_column(
        ForeignKey("investments.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(16))
    amount_minor: Mapped[int | None]
    occurred_on: Mapped[date | None] = mapped_column(Date)
    transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"), unique=True
    )
    note: Mapped[str] = mapped_column(String(200), default="")


class InvestmentValuationModel(TimestampMixin, Base):
    """The user-entered value of an investment on a date (one per day)."""

    __tablename__ = "investment_valuations"
    __table_args__ = (
        UniqueConstraint("investment_id", "valued_on", name="uq_investment_valuations_day"),
        CheckConstraint("value_minor >= 0", name="value_not_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    investment_id: Mapped[int] = mapped_column(
        ForeignKey("investments.id", ondelete="CASCADE"), index=True
    )
    valued_on: Mapped[date] = mapped_column(Date)
    value_minor: Mapped[int]
    note: Mapped[str] = mapped_column(String(200), default="")
