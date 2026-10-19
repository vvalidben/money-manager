"""Net worth over time: account balances plus investment values, month by month.

Each month is measured on its last day (the current month on today): the total
balance of every account opened by then, plus the latest value entered on or
before that day for each active investment. Investments never valued by then
count as nothing, the same rule as the Investments page's net worth.
"""

from collections.abc import Callable
from datetime import date

from money_manager.domain.investments import NetWorthPoint, value_on
from money_manager.domain.money import DEFAULT_CURRENCY, sum_money
from money_manager.domain.periods import add_months, month_end, month_start
from money_manager.persistence.database import Database
from money_manager.persistence.repositories import AccountRepository
from money_manager.services.balance_service import BalanceService
from money_manager.services.investment_service import InvestmentService

NET_WORTH_MONTHS = 12


class NetWorthService:
    def __init__(
        self,
        database: Database,
        balances: BalanceService,
        investments: InvestmentService,
        *,
        today: Callable[[], date] = date.today,
        base_currency: str = DEFAULT_CURRENCY,
    ) -> None:
        self._database = database
        self._balances = balances
        self._investments = investments
        self._today = today
        self._currency = base_currency

    def history(self, months: int = NET_WORTH_MONTHS, *,
                until: date | None = None) -> list[NetWorthPoint]:
        """One point per month, oldest first, from the first account's month (at most
        ``months`` of them, ending with the current month or ``until``'s month)."""
        today = self._today()
        if until is not None and month_start(until) < month_start(today):
            today = month_end(until)
        with self._database.session() as session:
            openings = [m.opening_date for m in AccountRepository(session).list_all()]
        if not openings:
            return []
        current = month_start(today)
        month = max(month_start(min(openings)), add_months(today, -(max(months, 1) - 1)))
        positions = self._investments.list()
        points: list[NetWorthPoint] = []
        while month <= current:
            day = today if month == current else month_end(month)
            values = (value_on(p.valuations, day) for p in positions)
            points.append(NetWorthPoint(
                month, day, self._balances.total_balance(day),
                sum_money((v for v in values if v is not None), self._currency)))
            month = add_months(month, 1)
        return points
