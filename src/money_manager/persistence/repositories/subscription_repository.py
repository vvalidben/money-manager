from collections.abc import Sequence
from datetime import date

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from money_manager.persistence.models import SubscriptionModel, SubscriptionPaymentModel


class SubscriptionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, subscription_id: int) -> SubscriptionModel | None:
        return self._session.get(SubscriptionModel, subscription_id)

    def list_all(self) -> Sequence[SubscriptionModel]:
        stmt = select(SubscriptionModel).order_by(SubscriptionModel.normalized_name)
        return self._session.scalars(stmt).all()

    def get_by_normalized_name(self, normalized_name: str) -> SubscriptionModel | None:
        stmt = select(SubscriptionModel).where(SubscriptionModel.normalized_name == normalized_name)
        return self._session.scalars(stmt).one_or_none()

    def exists_for_category(self, category_id: int) -> bool:
        stmt = select(exists().where(SubscriptionModel.category_id == category_id))
        return bool(self._session.scalar(stmt))

    def add(self, subscription: SubscriptionModel) -> SubscriptionModel:
        self._session.add(subscription)
        self._session.flush()
        return subscription

    def delete(self, subscription: SubscriptionModel) -> None:
        self._session.delete(subscription)
        self._session.flush()

    # ---------------------------------------------------------------- payments

    def payment_for(self, subscription_id: int, due_date: date) -> SubscriptionPaymentModel | None:
        stmt = select(SubscriptionPaymentModel).where(
            SubscriptionPaymentModel.subscription_id == subscription_id,
            SubscriptionPaymentModel.due_date == due_date,
        )
        return self._session.scalars(stmt).one_or_none()

    def payments(self, subscription_id: int) -> Sequence[SubscriptionPaymentModel]:
        stmt = (
            select(SubscriptionPaymentModel)
            .where(SubscriptionPaymentModel.subscription_id == subscription_id)
            .order_by(SubscriptionPaymentModel.due_date.desc())
        )
        return self._session.scalars(stmt).all()

    def add_payment(self, payment: SubscriptionPaymentModel) -> SubscriptionPaymentModel:
        self._session.add(payment)
        self._session.flush()
        return payment
