from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from money_manager.persistence.models import AIInsightModel


class AIInsightRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, insight_id: int) -> AIInsightModel | None:
        return self._session.get(AIInsightModel, insight_id)

    def recent(self, limit: int) -> Sequence[AIInsightModel]:
        """Newest first (ids break ties between insights stored in the same second)."""
        stmt = (select(AIInsightModel)
                .order_by(AIInsightModel.created_at.desc(), AIInsightModel.id.desc())
                .limit(limit))
        return self._session.scalars(stmt).all()

    def add(self, insight: AIInsightModel) -> AIInsightModel:
        self._session.add(insight)
        self._session.flush()
        return insight

    def delete(self, insight: AIInsightModel) -> None:
        self._session.delete(insight)
        self._session.flush()

    def delete_all(self) -> int:
        result = self._session.execute(delete(AIInsightModel))
        return int(getattr(result, "rowcount", 0) or 0)

    def keep_newest(self, count: int) -> None:
        """Delete everything but the ``count`` newest insights."""
        newest = (select(AIInsightModel.id)
                  .order_by(AIInsightModel.created_at.desc(), AIInsightModel.id.desc())
                  .limit(count))
        self._session.execute(delete(AIInsightModel).where(AIInsightModel.id.not_in(newest)))
