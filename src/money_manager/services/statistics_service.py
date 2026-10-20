"""Statistics for any date range, computed deterministically in one session.

Three grouped queries (daily balance changes, daily totals per type and
category, and the individual expenses of the last year for recurring
detection) feed the pure functions in ``domain.analytics``. See that module
for the definitions of spending, savings, investments and net change.
"""

import logging
from collections.abc import Callable
from datetime import date, datetime, timedelta

from money_manager.core.errors import ValidationError
from money_manager.domain.analytics import (
    RECURRING_LOOKBACK_DAYS,
    ExpenseRecord,
    LedgerEntry,
    balance_changes,
    balance_trend,
    category_changes,
    detect_recurring,
    monthly_summaries,
    period_totals,
    spending_by_category,
    spending_trend,
)
from money_manager.domain.money import DEFAULT_CURRENCY
from money_manager.domain.periods import (
    DateRange,
    StatsRange,
    add_months,
    month_start,
    previous_range,
    rolling_range,
)
from money_manager.domain.statistics import StatisticsReport
from money_manager.domain.validation import EARLIEST_ALLOWED_DATE
from money_manager.persistence.database import Database
from money_manager.persistence.mappers import category_to_domain
from money_manager.persistence.repositories import (
    AccountRepository,
    CategoryRepository,
    TransactionRepository,
)
from money_manager.services.currency import ensure_single_currency
from money_manager.core.i18n import tr

logger = logging.getLogger(__name__)

MAX_RANGE_DAYS = 3660  # ten years


class StatisticsService:
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

    def range_for(self, preset: StatsRange) -> DateRange:
        """The dates a preset (7 days, 30 days, 3/6 months, 1 year) covers today."""
        return rolling_range(preset, self._today())

    def custom_range(self, start: object, end: object) -> DateRange:
        """Validate user-picked dates and build a range."""
        for value, field in ((start, "start"), (end, "end")):
            if isinstance(value, datetime) or not isinstance(value, date):
                raise ValidationError(tr("Enter a valid calendar date."), field)
        assert isinstance(start, date) and isinstance(end, date)
        if start > end:
            raise ValidationError(tr("The start date must not be after the end date."), "start")
        period = DateRange(start, end)
        self._validate(period)
        return period

    def report(self, period: DateRange, previous: DateRange | None = None) -> StatisticsReport:
        """Figures for ``period``, compared with ``previous`` (default: the equally long
        range just before it)."""
        self._validate(period)
        previous = previous_range(period) if previous is None else previous
        first_month = month_start(period.start)
        # Also load the month before the first month (month-over-month baseline).
        window_start = min(previous.start, add_months(first_month, -1))
        lookback_start = period.end - timedelta(days=RECURRING_LOOKBACK_DAYS - 1)

        with self._database.session() as session:
            accounts = AccountRepository(session).list_all()
            ensure_single_currency(accounts, self._currency, tr("statistics page"))
            repository = TransactionRepository(session)
            daily = repository.daily_net_minor(until=period.end)
            entries = [LedgerEntry(*row) for row in repository.ledger_entries(window_start, period.end)]
            records = [
                ExpenseRecord(*row) for row in repository.expense_records(lookback_start, period.end)
            ]
            categories = [
                category_to_domain(m)
                for m in CategoryRepository(session).list(include_archived=True)
            ]
            openings = [(a.opening_date, a.opening_balance_minor) for a in accounts]

        currency = self._currency
        tracking_start = min((day for day, _ in openings), default=None)
        comparison_complete = tracking_start is not None and previous.start >= tracking_start
        names = {c.id: c.name for c in categories}
        investment_ids = frozenset(c.id for c in categories if c.is_investment)
        report = StatisticsReport(
            period=period,
            previous_period=previous,
            has_accounts=bool(openings),
            totals=period_totals(entries, period, investment_ids, currency),
            previous_totals=period_totals(entries, previous, investment_ids, currency),
            balance=balance_trend(balance_changes(openings, daily), period, currency),
            spending_by_category=spending_by_category(
                entries, period, names, investment_ids, currency
            ),
            category_changes=category_changes(
                entries, period, previous, names, investment_ids, currency
            ) if comparison_complete else (),
            months=monthly_summaries(entries, first_month, period.end, investment_ids, currency),
            trend=spending_trend(entries, period, investment_ids, currency),
            recurring=detect_recurring(records, period.end, currency),
            category_names=names,
            investment_category_ids=investment_ids,
            comparison_complete=comparison_complete,
        )
        logger.debug("Statistics computed for %s – %s", period.start, period.end)
        return report

    def _validate(self, period: DateRange) -> None:
        if not isinstance(period, DateRange):
            raise ValidationError(tr("Choose a date range."), "period")
        if period.end > self._today():
            raise ValidationError(tr("The range cannot end in the future."), "end")
        if period.start < EARLIEST_ALLOWED_DATE:
            raise ValidationError(
                tr("The range cannot start before {0}.", EARLIEST_ALLOWED_DATE.isoformat()), "start"
            )
        if period.days > MAX_RANGE_DAYS:
            raise ValidationError(tr("Choose a range of at most ten years."), "start")
