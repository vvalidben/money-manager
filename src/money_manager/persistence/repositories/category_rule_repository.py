from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from money_manager.persistence.models import CategoryRuleModel


class CategoryRuleRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self) -> Sequence[CategoryRuleModel]:
        return self._session.scalars(
            select(CategoryRuleModel).order_by(CategoryRuleModel.keyword,
                                               CategoryRuleModel.id)).all()

    def get(self, rule_id: int) -> CategoryRuleModel | None:
        return self._session.get(CategoryRuleModel, rule_id)

    def find(self, keyword: str, kind: str) -> CategoryRuleModel | None:
        return self._session.scalars(select(CategoryRuleModel).where(
            CategoryRuleModel.keyword == keyword, CategoryRuleModel.kind == kind)).first()

    def add(self, rule: CategoryRuleModel) -> CategoryRuleModel:
        self._session.add(rule)
        self._session.flush()
        return rule

    def delete(self, rule: CategoryRuleModel) -> None:
        self._session.delete(rule)
        self._session.flush()
