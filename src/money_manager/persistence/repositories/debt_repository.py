from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from money_manager.persistence.models import DebtModel, DebtPaymentModel


class DebtRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self) -> Sequence[DebtModel]:
        return self._session.scalars(
            select(DebtModel).order_by(DebtModel.start_date, DebtModel.id)).all()

    def get(self, debt_id: int) -> DebtModel | None:
        return self._session.get(DebtModel, debt_id)

    def payments(self) -> Sequence[DebtPaymentModel]:
        return self._session.scalars(select(DebtPaymentModel).order_by(
            DebtPaymentModel.paid_on, DebtPaymentModel.id)).all()

    def get_payment(self, payment_id: int) -> DebtPaymentModel | None:
        return self._session.get(DebtPaymentModel, payment_id)

    def add(self, model: DebtModel | DebtPaymentModel) -> None:
        self._session.add(model)
        self._session.flush()

    def delete(self, model: DebtModel | DebtPaymentModel) -> None:
        self._session.delete(model)
        self._session.flush()
