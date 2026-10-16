from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from money_manager.domain.validation import MAX_TRANSFER_NOTE_LENGTH
from money_manager.persistence.base import Base, TimestampMixin


class AllocationTransferModel(TimestampMixin, Base):
    """Money moved between allocations; NULL on either side means Available."""

    __tablename__ = "allocation_transfers"
    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="amount_positive"),
        # Rejects Available→Available (both NULL) and X→X in one rule.
        CheckConstraint(
            "COALESCE(from_allocation_id, 0) <> COALESCE(to_allocation_id, 0)",
            name="distinct_endpoints",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    from_allocation_id: Mapped[int | None] = mapped_column(
        ForeignKey("allocations.id", ondelete="RESTRICT"), index=True
    )
    to_allocation_id: Mapped[int | None] = mapped_column(
        ForeignKey("allocations.id", ondelete="RESTRICT"), index=True
    )
    amount_minor: Mapped[int]
    occurred_on: Mapped[date] = mapped_column(Date)
    note: Mapped[str] = mapped_column(String(MAX_TRANSFER_NOTE_LENGTH), default="")
