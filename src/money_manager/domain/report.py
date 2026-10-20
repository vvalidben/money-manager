"""The monthly report: one month's figures gathered for a printable summary."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

from money_manager.domain.analytics import MonthSummary
from money_manager.domain.budgets import BudgetSummary
from money_manager.domain.entities import Transaction
from money_manager.domain.goals import GoalProgress
from money_manager.domain.investments import NetWorthPoint
from money_manager.domain.money import Money
from money_manager.domain.periods import DateRange, month_end
from money_manager.domain.statistics import StatisticsReport

LARGEST_EXPENSES = 8
LARGEST_EXPENSES_OF_YEAR = 10


@dataclass(frozen=True, slots=True)
class MonthlyReport:
    month: date  # first day of the month
    period: DateRange  # the whole month, or up to today for the current month
    generated_on: date
    statistics: StatisticsReport  # totals, categories and comparison for ``period``
    budgets: BudgetSummary
    goals: tuple[GoalProgress, ...]  # as they stand on ``generated_on``
    net_worth: tuple[NetWorthPoint, ...]  # up to and including ``month``
    largest_expenses: tuple[Transaction, ...]
    category_names: Mapping[int, str]
    currency: str

    @property
    def is_complete(self) -> bool:
        """False for the current month, which is reported to date."""
        return self.period.end == month_end(self.month)

    @property
    def balance(self) -> Money | None:
        """Total balance at the end of the period."""
        return self.net_worth[-1].balance if self.net_worth else None


@dataclass(frozen=True, slots=True)
class YearlyReport:
    year: int
    period: DateRange  # 1 January to 31 December, or to today for the current year
    generated_on: date
    statistics: StatisticsReport  # vs the same days of the year before
    net_worth: tuple[NetWorthPoint, ...]  # each month of the year (from the first account)
    largest_expenses: tuple[Transaction, ...]
    category_names: Mapping[int, str]
    currency: str

    @property
    def is_complete(self) -> bool:
        return self.period.end == date(self.year, 12, 31)

    @property
    def months(self) -> tuple[MonthSummary, ...]:
        return self.statistics.months

    @property
    def best_month(self) -> MonthSummary | None:
        """The month that kept the most (income − spending)."""
        months = [m for m in self.months if not m.totals.income.is_zero()
                  or not m.totals.spending.is_zero()]
        return max(months, key=lambda m: (m.totals.savings, m.month), default=None)

    @property
    def worst_month(self) -> MonthSummary | None:
        months = [m for m in self.months if not m.totals.income.is_zero()
                  or not m.totals.spending.is_zero()]
        return min(months, key=lambda m: (m.totals.savings, m.month), default=None)
