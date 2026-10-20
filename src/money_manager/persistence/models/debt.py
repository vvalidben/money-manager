from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from money_manager.domain.debts import MAX_DEBT_NAME_LENGTH, DebtDirection
from money_manager.persistence.base import Base, TimestampMixin, in_values



class DebtModel(TimestampMixin, Base):
    """Money lent to someone or borrowed; repayments are ``DebtPaymentModel`` rows."""

    __tablename__ = "debts"
    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="amount_positive"),
        CheckConstraint(in_values("direction", DebtDirection), name="valid_direction"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(MAX_DEBT_NAME_LENGTH))
    direction: Mapped[str] = mapped_column(String(16))
    amount_minor: Mapped[int]
    start_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str] = mapped_column(Text, default="")
    # The adjustment that moved the money through an account, if any.
    transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"))


class DebtPaymentModel(TimestampMixin, Base):
    __tablename__ = "debt_payments"
    __table_args__ = (CheckConstraint("amount_minor > 0", name="amount_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    debt_id: Mapped[int] = mapped_column(ForeignKey("debts.id", ondelete="CASCADE"), index=True)
    amount_minor: Mapped[int]
    paid_on: Mapped[date] = mapped_column(Date)
    note: Mapped[str] = mapped_column(String(200), default="")
    transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"))
