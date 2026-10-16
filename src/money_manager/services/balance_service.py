"""Balance calculation and balance correction.

Balances are never stored. They are recomputed from the opening balance and
the per-type transaction totals every time, so editing or deleting a
transaction can never leave a stale or double-counted balance behind.
"""

import logging
from collections.abc import Callable
from datetime import date, datetime

from sqlalchemy.orm import Session

from money_manager.core.errors import NotFoundError, ValidationError
from money_manager.domain.balance import BalanceBreakdown
from money_manager.domain.entities import Transaction, TransactionDraft
from money_manager.domain.enums import TransactionType
from money_manager.domain.money import DEFAULT_CURRENCY, AmountInput, Money, parse_amount
from money_manager.domain.validation import is_record_id
from money_manager.persistence.database import Database
from money_manager.persistence.mappers import account_to_domain
from money_manager.persistence.repositories import AccountRepository, TransactionRepository
from money_manager.services.transaction_service import TransactionService

logger = logging.getLogger(__name__)

DEFAULT_CORRECTION_DESCRIPTION = "Balance correction"


class BalanceService:
    def __init__(
        self,
        database: Database,
        transactions: TransactionService,
        *,
        today: Callable[[], date] = date.today,
        base_currency: str = DEFAULT_CURRENCY,
    ) -> None:
        self._database = database
        self._transactions = transactions
        self._today = today
        self._base_currency = base_currency

    def breakdown(self, account_id: int, as_of: date | None = None) -> BalanceBreakdown:
        """Balance components, including transactions dated on or before ``as_of``.

        With ``as_of=None`` every recorded transaction is included.
        """
        with self._database.session() as session:
            return self._breakdown(session, account_id, as_of)

    def balance(self, account_id: int, as_of: date | None = None) -> Money:
        return self.breakdown(account_id, as_of).balance

    def total_balance(self, as_of: date | None = None) -> Money:
        """Sum of all account balances (accounts not yet opened on ``as_of`` count as zero)."""
        as_of = _check_as_of(as_of)
        total = Money.zero(self._base_currency)
        with self._database.session() as session:
            for model in AccountRepository(session).list_all():
                if as_of is not None and as_of < model.opening_date:
                    continue
                total = total + self._breakdown(session, model.id, as_of).balance
        return total

    def reconcile(
        self,
        account_id: int,
        actual_balance: AmountInput,
        *,
        on: date | None = None,
        description: str = DEFAULT_CORRECTION_DESCRIPTION,
    ) -> Transaction | None:
        """Make the recorded balance on ``on`` equal ``actual_balance``.

        Records the difference as a balance adjustment; the balance is never
        overwritten directly. Returns None when no correction is needed.
        """
        target_amount = parse_amount(actual_balance, "actual_balance")
        on_date = self._today() if on is None else on
        with self._database.session() as session:
            current = self._breakdown(session, account_id, on_date).balance
            difference = Money(target_amount, current.currency) - current
            if difference.is_zero():
                return None
            adjustment_type = (
                TransactionType.ADJUSTMENT_IN
                if difference.is_positive()
                else TransactionType.ADJUSTMENT_OUT
            )
            transaction = self._transactions.create_in_session(
                session,
                TransactionDraft(
                    account_id=account_id,
                    type=adjustment_type,
                    amount=abs(difference).amount,
                    occurred_on=on_date,
                    description=description,
                ),
            )
        logger.info("Recorded balance correction %s", transaction.id)
        return transaction

    @staticmethod
    def _breakdown(session: Session, account_id: int, as_of: date | None) -> BalanceBreakdown:
        as_of = _check_as_of(as_of)
        model = AccountRepository(session).get(account_id) if is_record_id(account_id) else None
        if model is None:
            raise NotFoundError(f"Account {account_id!r} does not exist.")
        account = account_to_domain(model)
        if as_of is not None and as_of < account.opening_date:
            raise ValidationError(
                f"No balance exists before the account's opening date "
                f"({account.opening_date.isoformat()}).",
                "as_of",
            )
        totals = TransactionRepository(session).totals_by_type(account.id, as_of)
        return BalanceBreakdown.from_totals(account.opening_balance, totals)


def _check_as_of(as_of: object) -> date | None:
    if as_of is None:
        return None
    if isinstance(as_of, datetime) or not isinstance(as_of, date):
        raise ValidationError("Enter a valid calendar date.", "as_of")
    return as_of
