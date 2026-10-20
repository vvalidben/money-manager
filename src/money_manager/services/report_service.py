"""The monthly report: gathers one month's figures from the other services.

Everything is read-only and computed locally; the report is written to a file
only by the user (see ``ui.reports``).
"""

from collections.abc import Callable
from datetime import date

from money_manager.core.errors import ValidationError
from money_manager.domain.entities import TransactionFilter
from money_manager.domain.enums import TransactionType
from money_manager.domain.periods import (
    DateRange,
    add_months,
    month_end,
    month_start,
    same_days_previous_month,
)
from money_manager.domain.report import (
    LARGEST_EXPENSES,
    LARGEST_EXPENSES_OF_YEAR,
    MonthlyReport,
    YearlyReport,
)
from money_manager.services.account_service import AccountService
from money_manager.services.budget_service import BudgetService
from money_manager.services.category_service import CategoryService
from money_manager.services.goal_service import GoalService
from money_manager.services.net_worth_service import NetWorthService
from money_manager.services.statistics_service import StatisticsService
from money_manager.services.transaction_service import TransactionService
from money_manager.core.i18n import tr


class ReportService:
    def __init__(
        self,
        *,
        accounts: AccountService,
        categories: CategoryService,
        transactions: TransactionService,
        statistics: StatisticsService,
        budgets: BudgetService,
        goals: GoalService,
        net_worth: NetWorthService,
        today: Callable[[], date] = date.today,
        base_currency: str,
    ) -> None:
        self._accounts = accounts
        self._categories = categories
        self._transactions = transactions
        self._statistics = statistics
        self._budgets = budgets
        self._goals = goals
        self._net_worth = net_worth
        self._today = today
        self._currency = base_currency

    def months(self) -> list[date]:
        """Months that can be reported, newest first (from the first account's month)."""
        openings = [a.opening_date for a in self._accounts.list()]
        today = self._today()
        if not openings or min(openings) > today:
            return []
        months, month = [], month_start(today)
        while month >= month_start(min(openings)):
            months.append(month)
            month = add_months(month, -1)
        return months

    def years(self) -> list[int]:
        """Years that can be reported, newest first."""
        return sorted({m.year for m in self.months()}, reverse=True)

    def yearly(self, year: int) -> YearlyReport:
        if isinstance(year, bool) or year not in self.years():
            raise ValidationError(tr("Choose a year between your first account and today."), "year")
        today = self._today()
        period = DateRange(date(year, 1, 1), min(date(year, 12, 31), today))
        previous = DateRange(date(year - 1, 1, 1),
                             _same_day(period.end, year - 1))
        expenses = self._transactions.list(TransactionFilter(
            types=frozenset({TransactionType.EXPENSE}), start=period.start, end=period.end))
        largest = sorted(expenses, key=lambda t: (-t.amount.amount, t.occurred_on, t.id))
        months_in_year = period.end.month
        return YearlyReport(
            year=year,
            period=period,
            generated_on=today,
            statistics=self._statistics.report(period, previous),
            net_worth=tuple(p for p in self._net_worth.history(months_in_year,
                                                               until=period.end)
                            if p.month.year == year),
            largest_expenses=tuple(largest[:LARGEST_EXPENSES_OF_YEAR]),
            category_names={c.id: c.name for c in
                            self._categories.list(include_archived=True)},
            currency=self._currency,
        )

    def monthly(self, month: date) -> MonthlyReport:
        if month_start(month) not in self.months():
            raise ValidationError(tr("Choose a month between your first account and today."),
                                  "month")
        today = self._today()
        start = month_start(month)
        period = DateRange(start, min(month_end(start), today))
        if period.end == month_end(start):  # a whole month: against the whole month before
            before = add_months(start, -1)
            previous = DateRange(before, month_end(before))
        else:  # month to date: against the same days of last month
            previous = same_days_previous_month(today)
        expenses = self._transactions.list(TransactionFilter(
            types=frozenset({TransactionType.EXPENSE}), start=period.start, end=period.end))
        largest = sorted(expenses, key=lambda t: (-t.amount.amount, t.occurred_on, t.id))
        return MonthlyReport(
            month=start,
            period=period,
            generated_on=today,
            statistics=self._statistics.report(period, previous),
            budgets=self._budgets.overview(start),
            goals=tuple(self._goals.list()),
            net_worth=tuple(self._net_worth.history(until=period.end)),
            largest_expenses=tuple(largest[:LARGEST_EXPENSES]),
            category_names={c.id: c.name for c in
                            self._categories.list(include_archived=True)},
            currency=self._currency,
        )


def _same_day(day: date, year: int) -> date:
    """``day`` in another year (29 February becomes the 28th)."""
    try:
        return day.replace(year=year)
    except ValueError:
        return day.replace(year=year, day=28)
