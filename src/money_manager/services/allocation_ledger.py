"""Current allocation state, computed inside one unit of work.

Everything is derived from the stored transactions and transfers each time;
no running balance is kept anywhere, so nothing can drift out of sync.
"""

from sqlalchemy.orm import Session

from money_manager.core.errors import CurrencyMismatchError, InsufficientFundsError
from money_manager.domain.allocation import AVAILABLE_LABEL, AllocationBalance, AllocationSummary
from money_manager.domain.entities import Allocation
from money_manager.domain.money import Money
from money_manager.persistence.mappers import allocation_to_domain
from money_manager.persistence.repositories import (
    AccountRepository,
    AllocationRepository,
    TransactionRepository,
)
from money_manager.core.i18n import tr


class AllocationLedger:
    def __init__(self, session: Session, currency: str) -> None:
        self._session = session
        self._currency = currency

    def total_balance(self) -> Money:
        """Real balance across all accounts: opening balances + every transaction."""
        accounts = AccountRepository(self._session).list_all()
        for account in accounts:
            if account.currency != self._currency:
                raise CurrencyMismatchError(
                    tr("Account '{0}' uses {1}; allocations are kept in {2}.", account.name, account.currency, self._currency)
                )
        opening_total = sum(account.opening_balance_minor for account in accounts)
        transactions_total = TransactionRepository(self._session).signed_total_minor()
        return Money.from_minor_units(opening_total + transactions_total, self._currency)

    def balances_minor(self) -> dict[int, int]:
        return AllocationRepository(self._session).balances_minor()

    def balance_of(self, allocation_id: int) -> Money:
        return Money.from_minor_units(self.balances_minor().get(allocation_id, 0), self._currency)

    def summary(self) -> AllocationSummary:
        """Active allocations plus any archived one that still holds money."""
        balances = self.balances_minor()
        rows = []
        for model in AllocationRepository(self._session).list(include_archived=True):
            balance = Money.from_minor_units(balances.get(model.id, 0), self._currency)
            if not model.is_archived or not balance.is_zero():
                rows.append(AllocationBalance(allocation_to_domain(model), balance))
        return AllocationSummary(total_balance=self.total_balance(), allocations=tuple(rows))

    def available(self) -> Money:
        return self.summary().available

    def require_funds(self, source: Allocation | None, amount: Money) -> None:
        """Raise unless ``source`` (None = Available) holds at least ``amount``."""
        if source is None:
            held, label = self.available(), tr(AVAILABLE_LABEL)
        else:
            held, label = self.balance_of(source.id), f"'{source.name}'"
        if held < amount:
            raise InsufficientFundsError(
                tr("{0} holds {1}; cannot move {2}.", label, held, amount), "amount"
            )
