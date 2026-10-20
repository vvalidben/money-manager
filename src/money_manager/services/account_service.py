"""Account use cases."""

import logging
from collections.abc import Callable
from datetime import date

from money_manager.core.errors import ConflictError, NotFoundError, ValidationError
from money_manager.domain.entities import Account
from money_manager.domain.money import DEFAULT_CURRENCY, AmountInput
from money_manager.domain.validation import is_record_id, normalize_name, validate_account
from money_manager.persistence.database import Database
from money_manager.persistence.mappers import account_to_domain
from money_manager.persistence.models import AccountModel
from money_manager.persistence.repositories import AccountRepository, TransactionRepository
from money_manager.core.i18n import tr

logger = logging.getLogger(__name__)


class AccountService:
    def __init__(
        self,
        database: Database,
        *,
        today: Callable[[], date] = date.today,
        default_currency: str = DEFAULT_CURRENCY,
    ) -> None:
        self._database = database
        self._today = today
        self._default_currency = default_currency

    def create(
        self,
        name: str,
        *,
        opening_balance: AmountInput = 0,
        opening_date: date | None = None,
        currency: str | None = None,
    ) -> Account:
        today = self._today()
        valid = validate_account(
            name=name,
            opening_balance=opening_balance,
            opening_date=today if opening_date is None else opening_date,
            currency=self._default_currency if currency is None else currency,
            today=today,
        )
        with self._database.session() as session:
            repository = AccountRepository(session)
            self._ensure_name_available(repository, valid.name)
            model = repository.add(
                AccountModel(
                    name=valid.name,
                    normalized_name=normalize_name(valid.name),
                    currency=valid.currency,
                    opening_balance_minor=valid.opening_balance.minor_units,
                    opening_date=valid.opening_date,
                )
            )
            account = account_to_domain(model)
        logger.info("Created account %s", account.id)
        return account

    def get(self, account_id: int) -> Account:
        with self._database.session() as session:
            return account_to_domain(_require(AccountRepository(session), account_id))

    def list(self) -> list[Account]:
        with self._database.session() as session:
            return [account_to_domain(m) for m in AccountRepository(session).list_all()]

    def update(
        self, account_id: int, *, name: str, opening_balance: AmountInput, opening_date: date
    ) -> Account:
        """Replace the editable fields. The currency cannot change."""
        with self._database.session() as session:
            repository = AccountRepository(session)
            model = _require(repository, account_id)
            valid = validate_account(
                name=name,
                opening_balance=opening_balance,
                opening_date=opening_date,
                currency=model.currency,
                today=self._today(),
            )
            self._ensure_name_available(repository, valid.name, exclude_id=model.id)

            first_transaction = TransactionRepository(session).earliest_date(model.id)
            if first_transaction is not None and valid.opening_date > first_transaction:
                raise ValidationError(
                    tr("The opening date cannot be after the account's first transaction ({0}).", first_transaction.isoformat()),
                    "opening_date",
                )

            model.name = valid.name
            model.normalized_name = normalize_name(valid.name)
            model.opening_balance_minor = valid.opening_balance.minor_units
            model.opening_date = valid.opening_date
            session.flush()
            account = account_to_domain(model)
        logger.info("Updated account %s", account.id)
        return account

    def delete(self, account_id: int) -> None:
        """Delete an account that has no transactions."""
        with self._database.session() as session:
            repository = AccountRepository(session)
            model = _require(repository, account_id)
            if TransactionRepository(session).exists_for_account(model.id):
                raise ConflictError(
                    tr("The account '{0}' has transactions and cannot be deleted.", model.name)
                )
            repository.delete(model)
        logger.info("Deleted account %s", account_id)

    @staticmethod
    def _ensure_name_available(
        repository: AccountRepository, name: str, exclude_id: int | None = None
    ) -> None:
        existing = repository.get_by_normalized_name(normalize_name(name))
        if existing is not None and existing.id != exclude_id:
            raise ConflictError(tr("An account named '{0}' already exists.", existing.name))


def _require(repository: AccountRepository, account_id: int) -> AccountModel:
    model = repository.get(account_id) if is_record_id(account_id) else None
    if model is None:
        raise NotFoundError(tr("Account {0!r} does not exist.", account_id))
    return model
