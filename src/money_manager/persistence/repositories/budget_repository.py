from collections.abc import Sequence
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from money_manager.domain.enums import TransactionType
from money_manager.persistence.models import BudgetModel, TransactionModel


class BudgetRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self) -> Sequence[BudgetModel]:
        return self._session.scalars(select(BudgetModel).order_by(BudgetModel.id)).all()

    def for_category(self, category_id: int) -> BudgetModel | None:
        return self._session.scalars(
            select(BudgetModel).where(BudgetModel.category_id == category_id)).first()

    def add(self, budget: BudgetModel) -> BudgetModel:
        self._session.add(budget)
        self._session.flush()
        return budget

    def delete(self, budget: BudgetModel) -> None:
        self._session.delete(budget)
        self._session.flush()

    def spent_minor(self, category_ids: Sequence[int], start: date, end: date) -> dict[int, int]:
        """Expense totals per category between ``start`` and ``end`` (inclusive)."""
        if not category_ids:
            return {}
        rows = self._session.execute(
            select(TransactionModel.category_id, func.sum(TransactionModel.amount_minor))
            .where(TransactionModel.type == TransactionType.EXPENSE.value,
                   TransactionModel.category_id.in_(category_ids),
                   TransactionModel.occurred_on >= start,
                   TransactionModel.occurred_on <= end)
            .group_by(TransactionModel.category_id))
        return {int(category_id): int(total) for category_id, total in rows}
