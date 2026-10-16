from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from money_manager.persistence.models import GoalModel


class GoalRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, goal_id: int) -> GoalModel | None:
        return self._session.get(GoalModel, goal_id)

    def list_all(self) -> Sequence[GoalModel]:
        return self._session.scalars(select(GoalModel).order_by(GoalModel.id)).all()

    def get_by_normalized_name(self, normalized_name: str) -> GoalModel | None:
        stmt = select(GoalModel).where(GoalModel.normalized_name == normalized_name)
        return self._session.scalars(stmt).one_or_none()

    def get_by_allocation(self, allocation_id: int) -> GoalModel | None:
        stmt = select(GoalModel).where(GoalModel.allocation_id == allocation_id)
        return self._session.scalars(stmt).one_or_none()

    def add(self, goal: GoalModel) -> GoalModel:
        self._session.add(goal)
        self._session.flush()
        return goal

    def delete(self, goal: GoalModel) -> None:
        self._session.delete(goal)
        self._session.flush()
