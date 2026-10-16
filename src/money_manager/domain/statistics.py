"""The statistics report: every analytic for one date range, precomputed."""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

from money_manager.domain.analytics import (
    BalanceTrend,
    CategoryAmount,
    CategoryChange,
    MonthSummary,
    PeriodTotals,
    RecurringExpense,
    SpendingTrend,
)
from money_manager.domain.health import relative_change
from money_manager.domain.money import Money, sum_money
from money_manager.domain.periods import DateRange

@dataclass(frozen=True, slots=True)
class StatisticsReport:
    period: DateRange
    previous_period: DateRange  # equally long, immediately before ``period``
    has_accounts: bool
    totals: PeriodTotals
    previous_totals: PeriodTotals
    balance: BalanceTrend
    spending_by_category: tuple[CategoryAmount, ...]
    category_changes: tuple[CategoryChange, ...]
    months: tuple[MonthSummary, ...]
    trend: SpendingTrend
    recurring: tuple[RecurringExpense, ...]
    category_names: Mapping[int, str]
    investment_category_ids: frozenset[int]
    # False when the previous period starts before tracking began: changes are
    # then unavailable instead of being compared with an incomplete period.
    comparison_complete: bool = True

    @property
    def income_change(self) -> Decimal | None:
        if not self.comparison_complete:
            return None
        return relative_change(self.totals.income, self.previous_totals.income)

    @property
    def expenses_change(self) -> Decimal | None:
        if not self.comparison_complete:
            return None
        return relative_change(self.totals.expenses, self.previous_totals.expenses)

    @property
    def spending_change(self) -> Decimal | None:
        if not self.comparison_complete:
            return None
        return relative_change(self.totals.spending, self.previous_totals.spending)

    @property
    def recurring_monthly_total(self) -> Money:
        return sum_money(
            (item.monthly_cost for item in self.recurring), self.totals.income.currency
        )

    @property
    def has_investment_categories(self) -> bool:
        return bool(self.investment_category_ids)
