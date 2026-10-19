from collections.abc import Sequence

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from money_manager.persistence.models import AccountTransferModel


class AccountTransferRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, transfer_id: int) -> AccountTransferModel | None:
        return self._session.get(AccountTransferModel, transfer_id)

    def for_transaction(self, transaction_id: int) -> AccountTransferModel | None:
        """The transfer this transaction is one side of, if any."""
        return self._session.scalars(select(AccountTransferModel).where(or_(
            AccountTransferModel.out_transaction_id == transaction_id,
            AccountTransferModel.in_transaction_id == transaction_id,
        ))).first()

    def list(self) -> Sequence[AccountTransferModel]:
        return self._session.scalars(
            select(AccountTransferModel).order_by(AccountTransferModel.id)).all()

    def add(self, transfer: AccountTransferModel) -> AccountTransferModel:
        self._session.add(transfer)
        self._session.flush()
        return transfer

    def delete(self, transfer: AccountTransferModel) -> None:
        self._session.delete(transfer)
        self._session.flush()
