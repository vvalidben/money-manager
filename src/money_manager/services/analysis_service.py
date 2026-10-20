"""Financial-health analysis: all metrics and facts for one period, in one session.

A handful of grouped queries feed the pure functions in
``domain.financial_analysis`` and ``domain.analytics``. No AI is involved;
the result (and its JSON form) is what a later AI step may interpret.
"""

import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import date, timedelta

from money_manager.core.errors import ValidationError
from money_manager.domain.analytics import (
    RECURRING_LOOKBACK_DAYS,
    ExpenseRecord,
    LedgerEntry,
    balance_changes,
    category_changes,
    detect_recurring,
    monthly_summaries,
    period_totals,
    spending_by_category,
)
from money_manager.domain.financial_analysis import (
    FinancialAnalysis,
    MonthValue,
    baseline_ranges,
    build_facts,
    comparison_range,
    detect_unusual_spending,
    month_end_balances,
    recurring_analysis,
    trend_months,
    trend_of,
)
from money_manager.domain.money import DEFAULT_CURRENCY, Money, sum_money
from money_manager.domain.periods import DateRange, add_months, month_end, month_start, month_to_date
from money_manager.domain.validation import EARLIEST_ALLOWED_DATE
from money_manager.persistence.database import Database
from money_manager.persistence.mappers import category_to_domain, subscription_to_domain
from money_manager.persistence.repositories import (
    AccountRepository,
    CategoryRepository,
    SubscriptionRepository,
    TransactionRepository,
)
from money_manager.services.currency import ensure_single_currency
from money_manager.services.statistics_service import MAX_RANGE_DAYS
from money_manager.core.i18n import tr

logger = logging.getLogger(__name__)

AVERAGE_SPENDING_MONTHS = 3


class FinancialAnalysisService:
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

    def analyze(self, period: DateRange | None = None) -> FinancialAnalysis:
        """Analyse ``period`` (default: the current month to date)."""
        today = self._today()
        period = month_to_date(today) if period is None else period
        self._validate(period, today)
        currency = self._currency
        comparison = comparison_range(period)
        baselines = baseline_ranges(period)

        with self._database.session() as session:
            accounts = AccountRepository(session).list_all()
            ensure_single_currency(accounts, currency, tr("financial analysis"))
            tracking_start = min((a.opening_date for a in accounts), default=None)
            months = trend_months(period.end, tracking_start)
            first_month = months[0] if months else month_start(period.start)
            window_start = min(comparison.start, baselines[-1].start, period.start,
                               add_months(first_month, -1))
            recurring_start = period.end - timedelta(days=RECURRING_LOOKBACK_DAYS - 1)
            repository = TransactionRepository(session)
            entries = [LedgerEntry(*row) for row in repository.ledger_entries(window_start,
                                                                               period.end)]
            records = [ExpenseRecord(*row) for row in repository.expense_records(
                min(recurring_start, baselines[-1].start), period.end)]
            daily = repository.daily_net_minor(until=period.end)
            categories = [category_to_domain(m) for m in
                          CategoryRepository(session).list(include_archived=True)]
            subscriptions = [s for s in (subscription_to_domain(m, currency) for m in
                                         SubscriptionRepository(session).list_all())
                             if s.is_active]
            openings = [(a.opening_date, a.opening_balance_minor) for a in accounts]

        names = {c.id: c.name for c in categories}
        investment_ids = frozenset(c.id for c in categories if c.is_investment)
        changes = balance_changes(openings, daily)
        month_totals = [(m, period_totals(entries, DateRange(m, month_end(m)), investment_ids,
                                          currency)) for m in months]
        recent = [totals.spending for _, totals in month_totals[-AVERAGE_SPENDING_MONTHS:]]
        average_spending = (
            Money.from_minor_units(sum_money(recent, currency).minor_units // len(recent), currency)
            if recent else None
        )

        analysis = FinancialAnalysis(
            period=period,
            comparison_period=comparison,
            has_accounts=bool(accounts),
            current_balance=Money.from_minor_units(
                sum(v for d, v in changes.items() if d <= period.end), currency),
            totals=period_totals(entries, period, investment_ids, currency),
            comparison_totals=period_totals(entries, comparison, investment_ids, currency),
            spending_by_category=spending_by_category(entries, period, names, investment_ids,
                                                      currency),
            category_changes=category_changes(entries, period, comparison, names, investment_ids,
                                              currency),
            monthly=monthly_summaries(entries, first_month, period.end, investment_ids, currency),
            income_trend=trend_of([MonthValue(m, t.income) for m, t in month_totals]),
            expense_trend=trend_of([MonthValue(m, t.spending) for m, t in month_totals]),
            balance_trend=trend_of(month_end_balances(changes, months, currency)),
            unusual_spending=detect_unusual_spending(entries, records, period, names,
                                                     investment_ids, currency, tracking_start),
            recurring=recurring_analysis(
                # Investing is not spending: investment categories are left out here.
                detect_recurring([r for r in records if r.day >= recurring_start
                                  and r.category_id not in investment_ids], period.end,
                                 currency),
                [s.name for s in subscriptions],
                sum_money((s.monthly_cost for s in subscriptions), currency),
                average_spending,
            ),
            comparison_complete=tracking_start is not None and comparison.start >= tracking_start,
            tracking_start=tracking_start,
        )
        logger.debug("Financial analysis for %s – %s", period.start, period.end)
        return replace(analysis, facts=build_facts(analysis))

    @staticmethod
    def _validate(period: DateRange, today: date) -> None:
        if not isinstance(period, DateRange):
            raise ValidationError(tr("Choose a period."), "period")
        if period.end > today:
            raise ValidationError(tr("The period cannot end in the future."), "end")
        if period.start < EARLIEST_ALLOWED_DATE:
            raise ValidationError(
                tr("The period cannot start before {0}.", EARLIEST_ALLOWED_DATE.isoformat()), "start")
        if period.days > MAX_RANGE_DAYS:
            raise ValidationError(tr("Choose a period of at most ten years."), "start")
