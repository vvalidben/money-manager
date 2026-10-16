"""Stored AI answers (insight history). Stays in the local database only."""

from datetime import date

from sqlalchemy import Boolean, CheckConstraint, Date, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from money_manager.domain.insights import InsightKind
from money_manager.persistence.base import Base, TimestampMixin, in_values


class AIInsightModel(TimestampMixin, Base):
    __tablename__ = "ai_insights"
    __table_args__ = (
        CheckConstraint(in_values("kind", InsightKind), name="valid_kind"),
        CheckConstraint("period_start <= period_end", name="period_in_order"),
        Index("ix_ai_insights_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))
    question: Mapped[str] = mapped_column(Text)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    provider: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(100))
    is_online: Mapped[bool] = mapped_column(Boolean)
    answer: Mapped[str] = mapped_column(Text)
    context: Mapped[str] = mapped_column(Text)
    truncated: Mapped[bool] = mapped_column(Boolean)

    def __repr__(self) -> str:
        return f"AIInsightModel(id={self.id!r}, kind={self.kind!r})"
