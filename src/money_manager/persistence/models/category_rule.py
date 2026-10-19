from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from money_manager.domain.categorize import MAX_KEYWORD_LENGTH
from money_manager.domain.enums import CategoryKind
from money_manager.persistence.base import Base, TimestampMixin, in_values


class CategoryRuleModel(TimestampMixin, Base):
    """A keyword that puts matching descriptions in a category (removed with it)."""

    __tablename__ = "category_rules"
    __table_args__ = (
        CheckConstraint(in_values("kind", CategoryKind), name="valid_kind"),
        UniqueConstraint("keyword", "kind"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    keyword: Mapped[str] = mapped_column(String(MAX_KEYWORD_LENGTH))
    kind: Mapped[str] = mapped_column(String(16))
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), index=True
    )
