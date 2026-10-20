from collections.abc import Collection, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from money_manager.persistence.models import ReceiptModel


class ReceiptRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def for_transaction(self, transaction_id: int) -> Sequence[ReceiptModel]:
        return self._session.scalars(select(ReceiptModel).where(
            ReceiptModel.transaction_id == transaction_id).order_by(ReceiptModel.id)).all()

    def counts(self, transaction_ids: Collection[int]) -> dict[int, int]:
        if not transaction_ids:
            return {}
        rows = self._session.execute(
            select(ReceiptModel.transaction_id, func.count())
            .where(ReceiptModel.transaction_id.in_(list(transaction_ids)))
            .group_by(ReceiptModel.transaction_id)).all()
        return {transaction_id: count for transaction_id, count in rows}

    def get(self, receipt_id: int) -> ReceiptModel | None:
        return self._session.get(ReceiptModel, receipt_id)

    def add(self, model: ReceiptModel) -> ReceiptModel:
        self._session.add(model)
        self._session.flush()
        return model

    def delete(self, model: ReceiptModel) -> None:
        self._session.delete(model)
        self._session.flush()
