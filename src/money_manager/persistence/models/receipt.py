from sqlalchemy import CheckConstraint, ForeignKey, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from money_manager.persistence.base import Base, TimestampMixin


class ReceiptModel(TimestampMixin, Base):
    """A receipt file attached to a transaction; the bytes live in the database so
    backups, safety copies and restores always include them."""

    __tablename__ = "receipts"
    __table_args__ = (CheckConstraint("size > 0", name="size_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"), index=True)
    file_name: Mapped[str] = mapped_column(String(200))
    media_type: Mapped[str] = mapped_column(String(40))
    size: Mapped[int]
    content: Mapped[bytes] = mapped_column(LargeBinary)
