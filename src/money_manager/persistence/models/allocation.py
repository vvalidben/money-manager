from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from money_manager.domain.validation import MAX_ALLOCATION_NAME_LENGTH
from money_manager.persistence.base import Base, TimestampMixin


class AllocationModel(TimestampMixin, Base):
    """A user-named allocation. Its balance is derived, never stored."""

    __tablename__ = "allocations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(MAX_ALLOCATION_NAME_LENGTH))
    normalized_name: Mapped[str] = mapped_column(String(MAX_ALLOCATION_NAME_LENGTH), unique=True)
    is_archived: Mapped[bool] = mapped_column(default=False)
