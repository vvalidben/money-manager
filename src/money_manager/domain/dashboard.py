"""Read-only snapshot of everything the dashboard shows."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from money_manager.domain.allocation import AllocationSummary
from money_manager.domain.analytics import BalancePoint
from money_manager.domain.entities import Transaction
from money_manager.domain.goals import GoalProgress
from money_manager.domain.health import HealthMetrics
from money_manager.domain.money import Money
from money_manager.domain.periods import DateRange


@dataclass(frozen=True, slots=True)
class MonthlyFlow:
    """Income and expenses of one calendar month (adjustments excluded)."""

    month: date  # first day of the month
    income: Money
    expenses: Money

    @property
    def net(self) -> Money:
        return self.income - self.expenses


@dataclass(frozen=True, slots=True)
class CategorySpending:
    category_id: int | None  # None for the folded "Other" row
    name: str
    amount: Money
    share: Decimal | None  # fraction of the period's expenses


@dataclass(frozen=True, slots=True)
class AllocationSlice:
    allocation_id: int | None  # None for Available
    name: str
    amount: Money
    share: Decimal | None  # fraction of the total balance


@dataclass(frozen=True, slots=True)
class DashboardOverview:
    period: DateRange
    has_accounts: bool
    total_balance: Money
    income: Money
    expenses: Money
    investments: Money  # part of ``expenses`` spent in investment categories
    previous_period: DateRange
    previous_period_expenses: Money
    allocation: AllocationSummary
    allocation_slices: tuple[AllocationSlice, ...]
    recent_transactions: tuple[Transaction, ...]
    category_names: Mapping[int, str]
    allocation_names: Mapping[int, str]
    monthly_flows: tuple[MonthlyFlow, ...]
    balance_history: tuple[BalancePoint, ...]
    spending_by_category: tuple[CategorySpending, ...]
    health: HealthMetrics
    goals: tuple[GoalProgress, ...] = ()  # unfinished first, nearest deadline first

    @property
    def spending(self) -> Money:
        """Expenses that were consumed, i.e. not invested."""
        return self.expenses - self.investments

    @property
    def savings(self) -> Money:
        """Money kept or invested this period: income − spending (negative = overspent)."""
        return self.income - self.spending
