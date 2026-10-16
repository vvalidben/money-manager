from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from money_manager.persistence.models import AccountModel


class AccountRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, account_id: int) -> AccountModel | None:
        return self._session.get(AccountModel, account_id)

    def list_all(self) -> Sequence[AccountModel]:
        stmt = select(AccountModel).order_by(AccountModel.normalized_name, AccountModel.id)
        return self._session.scalars(stmt).all()

    def get_by_normalized_name(self, normalized_name: str) -> AccountModel | None:
        stmt = select(AccountModel).where(AccountModel.normalized_name == normalized_name)
        return self._session.scalars(stmt).one_or_none()

    def add(self, account: AccountModel) -> AccountModel:
        self._session.add(account)
        self._session.flush()
        return account

    def delete(self, account: AccountModel) -> None:
        self._session.delete(account)
        self._session.flush()
