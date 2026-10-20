"""Everything the dashboard shows, computed in one database session.

A handful of grouped queries feed all cards, charts and metrics, so opening
the dashboard costs the same few queries regardless of how much data exists.
The calculations themselves are the shared, pure functions in
``domain.analytics`` (see there for the definitions of spending, savings and
investments), so the dashboard and the statistics page always agree.

Dashboard specifics
-------------------
* Period: the current month to date (1st .. today).
* Balance history: the last 180 days (from the first account's opening).
* Average monthly spending (for runway): mean of the last three complete
  months that fall on or after the first account's opening month.
"""

from collections.abc import Callable, Sequence
from datetime import date, timedelta

from money_manager.core.i18n import tr
from money_manager.domain.allocation import AVAILABLE_LABEL, AllocationBalance, AllocationSummary
from money_manager.domain.analytics import (
    LedgerEntry,
    PeriodTotals,
    balance_changes,
    balance_trend,
    period_totals,
    spending_by_category,
)
from money_manager.domain.dashboard import (
    AllocationSlice,
    CategorySpending,
    DashboardOverview,
    MonthlyFlow,
)
from money_manager.domain.entities import TransactionFilter
from money_manager.domain.enums import TransactionSort
from money_manager.domain.goals import order_goals
from money_manager.domain.health import (
    HealthMetrics,
    ratio,
    runway_months,
    spending_change,
)
from money_manager.domain.money import DEFAULT_CURRENCY, Money, sum_money
from money_manager.domain.periods import (
    DateRange,
    add_months,
    month_end,
    month_start,
    month_to_date,
    same_days_previous_month,
)
from money_manager.persistence.database import Database
from money_manager.persistence.mappers import (
    allocation_to_domain,
    category_to_domain,
    transaction_to_domain,
)
from money_manager.persistence.models import AccountModel
from money_manager.persistence.repositories import (
    AccountRepository,
    AllocationRepository,
    CategoryRepository,
    GoalRepository,
    TransactionRepository,
)
from money_manager.services.currency import ensure_single_currency
from money_manager.services.goal_service import build_goal_progress

RECENT_TRANSACTIONS = 8
FLOW_MONTHS = 6
HISTORY_DAYS = 180
TOP_CATEGORIES = 5
RUNWAY_MONTHS_SAMPLE = 3
OTHER_CATEGORY_LABEL = "Other"


class DashboardService:
    def __init__(
        self,
        database: Database,
        *,
        today: Callable[[], date] = date.today,
        base_currency: str = DEFAULT_CURRENCY,
    ) -> None:
        self._database = database
        self._today = today
        self._currency = base_currency

    def overview(self) -> DashboardOverview:
        today = self._today()
        period = month_to_date(today)
        previous_period = same_days_previous_month(today)
        flow_start = add_months(today, -(FLOW_MONTHS - 1))

        with self._database.session() as session:
            accounts = AccountRepository(session).list_all()
            ensure_single_currency(accounts, self._currency, "dashboard")
            transactions = TransactionRepository(session)
            daily = transactions.daily_net_minor(until=today)
            entries = [LedgerEntry(*row) for row in transactions.ledger_entries(flow_start, today)]
            recent = transactions.search(
                TransactionFilter(end=today),
                TransactionSort.DATE,
                descending=True,
                limit=RECENT_TRANSACTIONS,
            )
            categories = [category_to_domain(m) for m in CategoryRepository(session).list(
                include_archived=True)]
            allocation_models = AllocationRepository(session).list(include_archived=True)
            allocation_balances = AllocationRepository(session).balances_minor()
            goal_models = GoalRepository(session).list_all()
            recent_transactions = tuple(transaction_to_domain(m) for m in recent)
            allocations = [allocation_to_domain(m) for m in allocation_models]

        investment_ids = frozenset(c.id for c in categories if c.is_investment)
        category_names = {c.id: c.name for c in categories}
        month_totals = self._month_totals(entries, flow_start, today, investment_ids)
        current = period_totals(entries, period, investment_ids, self._currency)
        previous = period_totals(entries, previous_period, investment_ids, self._currency)
        total_balance, history = self._balance_history(accounts, daily, today)

        allocation_summary = AllocationSummary(
            total_balance=total_balance,
            allocations=tuple(
                AllocationBalance(allocation, self._money(allocation_balances.get(allocation.id, 0)))
                for allocation in allocations
                if not allocation.is_archived or allocation_balances.get(allocation.id, 0)
            ),
        )

        allocation_names = {a.id: a.name for a in allocations}
        goals = order_goals([
            build_goal_progress(model, allocation_balances, allocation_names, self._currency, today)
            for model in goal_models
        ])

        return DashboardOverview(
            period=period,
            has_accounts=bool(accounts),
            total_balance=total_balance,
            income=current.income,
            expenses=current.expenses,
            investments=current.investments,
            previous_period=previous_period,
            previous_period_expenses=previous.expenses,
            allocation=allocation_summary,
            allocation_slices=self._allocation_slices(allocation_summary),
            recent_transactions=recent_transactions,
            category_names=category_names,
            allocation_names=allocation_names,
            monthly_flows=tuple(
                MonthlyFlow(month, totals.income, totals.expenses) for month, totals in month_totals
            ),
            balance_history=history,
            spending_by_category=self._top_categories(
                entries, period, category_names, investment_ids
            ),
            health=HealthMetrics(
                savings_rate=current.savings_rate,
                spending_change=spending_change(current.spending, previous.spending),
                runway_months=runway_months(
                    total_balance, self._average_monthly_spending(month_totals, accounts)
                ),
                allocated_share=(
                    ratio(allocation_summary.allocated_total, total_balance)
                    if total_balance.is_positive()
                    else None
                ),
            ),
            goals=goals,
        )

    # ------------------------------------------------------------ calculations

    def _money(self, minor_units: int) -> Money:
        return Money.from_minor_units(minor_units, self._currency)

    def _month_totals(
        self,
        entries: Sequence[LedgerEntry],
        first_month: date,
        today: date,
        investment_ids: frozenset[int],
    ) -> list[tuple[date, PeriodTotals]]:
        months = []
        month = first_month
        while month <= today:
            span = DateRange(month, min(month_end(month), today))
            months.append((month, period_totals(entries, span, investment_ids, self._currency)))
            month = add_months(month, 1)
        return months

    def _balance_history(
        self, accounts: Sequence[AccountModel], daily: Sequence[tuple[date, int]], today: date
    ) -> tuple[Money, tuple]:
        """Total balance today plus one end-of-day point per day of the window."""
        changes = balance_changes(
            ((a.opening_date, a.opening_balance_minor) for a in accounts), daily
        )
        if not accounts:
            return self._money(sum(v for d, v in changes.items() if d <= today)), ()
        first_opening = min(account.opening_date for account in accounts)
        start = max(today - timedelta(days=HISTORY_DAYS - 1), first_opening)
        trend = balance_trend(changes, DateRange(start, today), self._currency)
        return trend.closing, trend.points

    def _average_monthly_spending(
        self, month_totals: Sequence[tuple[date, PeriodTotals]], accounts: Sequence[AccountModel]
    ) -> Money | None:
        if not accounts:
            return None
        tracked_from = month_start(min(account.opening_date for account in accounts))
        complete = [totals for month, totals in month_totals[:-1] if month >= tracked_from]
        sample = complete[-RUNWAY_MONTHS_SAMPLE:]
        if not sample:
            return None
        total = sum_money((totals.spending for totals in sample), self._currency)
        # Exact to the centime; the remainder of the division is dropped.
        return self._money(total.minor_units // len(sample))

    def _top_categories(
        self,
        entries: Sequence[LedgerEntry],
        period: DateRange,
        names: dict[int, str],
        investment_ids: frozenset[int],
    ) -> tuple[CategorySpending, ...]:
        rows = spending_by_category(entries, period, names, investment_ids, self._currency)
        top = [
            CategorySpending(row.category_id, row.name, row.amount, row.share)
            for row in rows[:TOP_CATEGORIES]
        ]
        rest = rows[TOP_CATEGORIES:]
        if rest:
            other = sum_money((row.amount for row in rest), self._currency)
            grand_total = sum_money((row.amount for row in rows), self._currency)
            top.append(
                CategorySpending(None, OTHER_CATEGORY_LABEL, other, ratio(other, grand_total))
            )
        return tuple(top)

    @staticmethod
    def _allocation_slices(summary: AllocationSummary) -> tuple[AllocationSlice, ...]:
        total = summary.total_balance
        slices = [
            AllocationSlice(
                allocation_id=row.allocation.id,
                name=row.allocation.name,
                amount=row.balance,
                share=ratio(row.balance, total) if total.is_positive() else None,
            )
            for row in sorted(summary.allocations, key=lambda r: r.balance, reverse=True)
        ]
        slices.append(
            AllocationSlice(
                allocation_id=None,
                name=tr(AVAILABLE_LABEL),
                amount=summary.available,
                share=ratio(summary.available, total) if total.is_positive() else None,
            )
        )
        return tuple(slices)
