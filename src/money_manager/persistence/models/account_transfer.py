from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from money_manager.persistence.base import Base, TimestampMixin


class AccountTransferModel(TimestampMixin, Base):
    """Money moved between two of the user's accounts.

    The movement itself is two balance adjustments (out of one account, into
    the other), so balances need no special case and a transfer is never
    income or spending. This row ties the two together; RESTRICT keeps either
    side from being deleted on its own.
    """

    __tablename__ = "account_transfers"
    __table_args__ = (
        CheckConstraint("out_transaction_id <> in_transaction_id", name="distinct_sides"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    out_transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="RESTRICT"), unique=True
    )
    in_transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="RESTRICT"), unique=True
    )
