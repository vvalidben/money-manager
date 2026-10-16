from sqlalchemy import CheckConstraint, String, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column

from money_manager.domain.enums import CategoryKind
from money_manager.domain.validation import MAX_CATEGORY_NAME_LENGTH
from money_manager.persistence.base import Base, TimestampMixin, in_values


class CategoryModel(TimestampMixin, Base):
    """User-created label for income or expenses. Nothing is pre-seeded."""

    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("kind", "normalized_name"),
        CheckConstraint(in_values("kind", CategoryKind), name="valid_kind"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(MAX_CATEGORY_NAME_LENGTH))
    normalized_name: Mapped[str] = mapped_column(String(MAX_CATEGORY_NAME_LENGTH))
    kind: Mapped[str] = mapped_column(String(16))
    is_archived: Mapped[bool] = mapped_column(default=False)
    # Expense categories whose spending is money invested rather than consumed.
    is_investment: Mapped[bool] = mapped_column(default=False, server_default=false())
