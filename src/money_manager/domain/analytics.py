"""Deterministic analytics over aggregated ledger rows.

Every function here is pure: the same rows always give the same result, all
money arithmetic is on integer minor units or ``Money``, and ratios use exact
``Decimal`` division rounded half-up to four places. The statistics service
feeds these functions; AI features may later *interpret* the results but
never compute them.

Definitions
-----------
* **Expenses:** every expense transaction (money that left the accounts).
* **Investment contributions:** expenses in categories marked as investments.
* **Spending:** expenses − investment contributions (money actually consumed).
* **Savings:** income − spending (money kept or invested).
* **Savings rate:** savings ÷ income. **Investment rate:** investments ÷ income.
* **Net change:** change in the real balance: income − expenses ± adjustments.
* Balance adjustments are corrections: they move the balance but are never
  income, spending or savings.
"""

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from itertools import pairwise

from money_manager.domain.enums import TransactionType
from money_manager.domain.health import RATIO_QUANTUM, ratio, relative_change, savings_rate
from money_manager.domain.money import Money
from money_manager.domain.periods import (
    DateRange,
    add_months,
    month_end,
    month_start,
    same_days_previous_month,
)
from money_manager.domain.validation import normalize_name
from money_manager.core.i18n import tr

# --------------------------------------------------------------------- inputs


@dataclass(frozen=True, slots=True)
class LedgerEntry:
    """Sum of transaction amounts for one day, type and category."""

    day: date
    type: TransactionType
    category_id: int | None
    amount_minor: int  # positive


@dataclass(frozen=True, slots=True)
class ExpenseRecord:
    """A single expense, used for recurring-spending detection."""

    day: date
    description: str
    category_id: int | None
    amount_minor: int


# ------------------------------------------------------------ period totals


@dataclass(frozen=True, slots=True)
class PeriodTotals:
    income: Money
    expenses: Money
    investments: Money
    adjustments_in: Money
    adjustments_out: Money

    @property
    def spending(self) -> Money:
        return self.expenses - self.investments

    @property
    def savings(self) -> Money:
        return self.income - self.spending

    @property
    def net_change(self) -> Money:
        return self.income - self.expenses + self.adjustments_in - self.adjustments_out

    @property
    def savings_rate(self) -> Decimal | None:
        return savings_rate(self.income, self.spending)

    @property
    def investment_rate(self) -> Decimal | None:
        return ratio(self.investments, self.income) if self.income.is_positive() else None


def period_totals(
    entries: Iterable[LedgerEntry],
    period: DateRange,
    investment_ids: frozenset[int],
    currency: str,
) -> PeriodTotals:
    sums: defaultdict[TransactionType, int] = defaultdict(int)
    invested = 0
    for entry in entries:
        if entry.day not in period:
            continue
        sums[entry.type] += entry.amount_minor
        if entry.type is TransactionType.EXPENSE and entry.category_id in investment_ids:
            invested += entry.amount_minor

    def money(minor: int) -> Money:
        return Money.from_minor_units(minor, currency)

    return PeriodTotals(
        income=money(sums[TransactionType.INCOME]),
        expenses=money(sums[TransactionType.EXPENSE]),
        investments=money(invested),
        adjustments_in=money(sums[TransactionType.ADJUSTMENT_IN]),
        adjustments_out=money(sums[TransactionType.ADJUSTMENT_OUT]),
    )


def _spending_by_category(
    entries: Iterable[LedgerEntry], period: DateRange, investment_ids: frozenset[int]
) -> dict[int | None, int]:
    totals: defaultdict[int | None, int] = defaultdict(int)
    for entry in entries:
        if (
            entry.type is TransactionType.EXPENSE
            and entry.day in period
            and entry.category_id not in investment_ids
        ):
            totals[entry.category_id] += entry.amount_minor
    return dict(totals)


# ------------------------------------------------------------- categories


@dataclass(frozen=True, slots=True)
class CategoryAmount:
    category_id: int | None
    name: str
    amount: Money
    share: Decimal | None  # fraction of the period's spending


def spending_by_category(
    entries: Iterable[LedgerEntry],
    period: DateRange,
    names: Mapping[int, str],
    investment_ids: frozenset[int],
    currency: str,
) -> tuple[CategoryAmount, ...]:
    """Spending (investments excluded) per category, largest first."""
    totals = _spending_by_category(entries, period, investment_ids)
    grand_total = Money.from_minor_units(sum(totals.values()), currency)
    rows = [
        CategoryAmount(
            category_id=category_id,
            name=_name(names, category_id),
            amount=Money.from_minor_units(amount, currency),
            share=ratio(Money.from_minor_units(amount, currency), grand_total),
        )
        for category_id, amount in totals.items()
    ]
    rows.sort(key=lambda row: (-row.amount.minor_units, row.name.casefold(), row.category_id or 0))
    return tuple(rows)


@dataclass(frozen=True, slots=True)
class CategoryChange:
    category_id: int | None
    name: str
    previous: Money
    current: Money

    @property
    def change(self) -> Money:
        return self.current - self.previous

    @property
    def change_ratio(self) -> Decimal | None:
        """None when there was no spending before (a new category)."""
        return relative_change(self.current, self.previous)

    @property
    def is_new(self) -> bool:
        return self.previous.is_zero() and self.current.is_positive()


def category_changes(
    entries: Sequence[LedgerEntry],
    current: DateRange,
    previous: DateRange,
    names: Mapping[int, str],
    investment_ids: frozenset[int],
    currency: str,
) -> tuple[CategoryChange, ...]:
    """Spending per category in ``current`` vs ``previous``, biggest movement first."""
    now = _spending_by_category(entries, current, investment_ids)
    before = _spending_by_category(entries, previous, investment_ids)
    rows = [
        CategoryChange(
            category_id=category_id,
            name=_name(names, category_id),
            previous=Money.from_minor_units(before.get(category_id, 0), currency),
            current=Money.from_minor_units(now.get(category_id, 0), currency),
        )
        for category_id in now.keys() | before.keys()
    ]
    rows.sort(key=lambda row: (-abs(row.change.minor_units), row.name.casefold(),
                               row.category_id or 0))
    return tuple(rows)


# ----------------------------------------------------------------- months


@dataclass(frozen=True, slots=True)
class MonthSummary:
    month: date  # first day of the month
    totals: PeriodTotals
    is_partial: bool  # the month is not over yet (compared on the same days)
    income_change: Decimal | None
    spending_change: Decimal | None


def monthly_summaries(
    entries: Sequence[LedgerEntry],
    first_month: date,
    last_day: date,
    investment_ids: frozenset[int],
    currency: str,
) -> tuple[MonthSummary, ...]:
    """One summary per calendar month from ``first_month`` to ``last_day``'s month.

    Month-over-month changes compare with the previous full month; a month
    still in progress is compared with the same days of the previous month.
    ``entries`` must also cover the month before ``first_month``.
    """
    summaries = []
    month = month_start(first_month)
    while month <= last_day:
        is_partial = month_end(month) > last_day
        current = DateRange(month, min(month_end(month), last_day))
        if is_partial:
            baseline = same_days_previous_month(last_day)
        else:
            previous_month = add_months(month, -1)
            baseline = DateRange(previous_month, month_end(previous_month))
        now = period_totals(entries, current, investment_ids, currency)
        before = period_totals(entries, baseline, investment_ids, currency)
        summaries.append(
            MonthSummary(
                month=month,
                totals=now,
                is_partial=is_partial,
                income_change=relative_change(now.income, before.income),
                spending_change=relative_change(now.spending, before.spending),
            )
        )
        month = add_months(month, 1)
    return tuple(summaries)


# ------------------------------------------------------------------ trend


class Granularity(StrEnum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class TrendDirection(StrEnum):
    RISING = "rising"
    FALLING = "falling"
    STABLE = "stable"
    NO_DATA = "no_data"


STABLE_BAND = Decimal("0.05")  # within ±5 % counts as stable
DAILY_BUCKETS_MAX_DAYS = 31
WEEKLY_BUCKETS_MAX_DAYS = 186


@dataclass(frozen=True, slots=True)
class TrendBucket:
    period: DateRange
    spending: Money


@dataclass(frozen=True, slots=True)
class SpendingTrend:
    granularity: Granularity
    buckets: tuple[TrendBucket, ...]
    average_per_day: Money
    change: Decimal | None  # daily average, second half of the range vs first half
    direction: TrendDirection


def granularity_for(period: DateRange) -> Granularity:
    if period.days <= DAILY_BUCKETS_MAX_DAYS:
        return Granularity.DAY
    if period.days <= WEEKLY_BUCKETS_MAX_DAYS:
        return Granularity.WEEK
    return Granularity.MONTH


def bucket_ranges(period: DateRange, granularity: Granularity) -> tuple[DateRange, ...]:
    """Consecutive ranges covering ``period``; weeks start on Monday, months on the 1st."""
    ranges = []
    start = period.start
    while start <= period.end:
        match granularity:
            case Granularity.DAY:
                end = start
            case Granularity.WEEK:
                end = start + timedelta(days=6 - start.weekday())
            case Granularity.MONTH:
                end = month_end(start)
        end = min(end, period.end)
        ranges.append(DateRange(start, end))
        start = end + timedelta(days=1)
    return tuple(ranges)


def spending_trend(
    entries: Sequence[LedgerEntry],
    period: DateRange,
    investment_ids: frozenset[int],
    currency: str,
) -> SpendingTrend:
    daily: defaultdict[date, int] = defaultdict(int)
    for entry in entries:
        if (
            entry.type is TransactionType.EXPENSE
            and entry.day in period
            and entry.category_id not in investment_ids
        ):
            daily[entry.day] += entry.amount_minor

    granularity = granularity_for(period)
    buckets = tuple(
        TrendBucket(
            bucket,
            Money.from_minor_units(
                sum(amount for day, amount in daily.items() if day in bucket), currency
            ),
        )
        for bucket in bucket_ranges(period, granularity)
    )
    total = sum(daily.values())
    average = (Decimal(total) / period.days).quantize(Decimal(1), rounding=ROUND_HALF_UP)

    change: Decimal | None = None
    direction = TrendDirection.NO_DATA
    if period.days >= 2 and total:
        first_days = period.days // 2
        split = period.start + timedelta(days=first_days)
        first = sum(amount for day, amount in daily.items() if day < split)
        second = total - first
        first_avg = Decimal(first) / first_days
        second_avg = Decimal(second) / (period.days - first_days)
        if first_avg == 0:
            direction = TrendDirection.RISING
        else:
            change = ((second_avg - first_avg) / first_avg).quantize(
                RATIO_QUANTUM, rounding=ROUND_HALF_UP
            )
            if abs(change) <= STABLE_BAND:
                direction = TrendDirection.STABLE
            else:
                direction = TrendDirection.RISING if change > 0 else TrendDirection.FALLING

    return SpendingTrend(
        granularity=granularity,
        buckets=buckets,
        average_per_day=Money.from_minor_units(int(average), currency),
        change=change,
        direction=direction,
    )


# ---------------------------------------------------------------- balance


@dataclass(frozen=True, slots=True)
class BalancePoint:
    day: date
    balance: Money  # total real balance at the end of ``day``


@dataclass(frozen=True, slots=True)
class BalanceTrend:
    opening: Money  # balance at the end of the day before the range
    closing: Money
    points: tuple[BalancePoint, ...]

    @property
    def change(self) -> Money:
        return self.closing - self.opening

    @property
    def change_ratio(self) -> Decimal | None:
        return relative_change(self.closing, self.opening)


def balance_changes(
    openings: Iterable[tuple[date, int]], daily_nets: Iterable[tuple[date, int]]
) -> dict[date, int]:
    """Per-day change of the total balance: opening balances count on their opening date."""
    changes: defaultdict[date, int] = defaultdict(int)
    for day, amount in openings:
        changes[day] += amount
    for day, amount in daily_nets:
        changes[day] += amount
    return dict(changes)


def balance_trend(changes: Mapping[date, int], period: DateRange, currency: str) -> BalanceTrend:
    """End-of-day balances for every day of ``period``."""
    running = sum(amount for day, amount in changes.items() if day < period.start)
    opening = running
    points = []
    day = period.start
    while day <= period.end:
        running += changes.get(day, 0)
        points.append(BalancePoint(day, Money.from_minor_units(running, currency)))
        day += timedelta(days=1)
    return BalanceTrend(
        opening=Money.from_minor_units(opening, currency),
        closing=Money.from_minor_units(running, currency),
        points=tuple(points),
    )


# -------------------------------------------------------------- recurring


class Cadence(StrEnum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"


RECURRING_MIN_OCCURRENCES = 3
RECURRING_LOOKBACK_DAYS = 365
_CADENCE_GAP_DAYS = {Cadence.WEEKLY: (6, 8), Cadence.MONTHLY: (26, 35)}
_GAP_TOLERANCE = Decimal("0.4")  # every gap within ±40 % of the typical gap
_MAX_AMOUNT_SPREAD = 2  # largest amount at most twice the smallest
_OVERDUE_FACTOR = Decimal("1.5")  # silent for 1.5 cycles = no longer recurring
_WEEKS_PER_MONTH = Decimal(52) / Decimal(12)


@dataclass(frozen=True, slots=True)
class RecurringExpense:
    label: str
    category_id: int | None
    cadence: Cadence
    typical_amount: Money  # median of the occurrences
    occurrences: int
    first_seen: date
    last_seen: date
    next_expected: date
    monthly_cost: Money
    is_fixed_amount: bool


def detect_recurring(
    records: Iterable[ExpenseRecord], as_of: date, currency: str
) -> tuple[RecurringExpense, ...]:
    """Find expenses that repeat weekly or monthly with a similar amount.

    Expenses are grouped by (description, category), ignoring case and extra
    spaces; undescribed expenses are skipped. A group qualifies with at least
    three occurrences, regular gaps that match a cadence, amounts within a
    factor of two, and a latest occurrence recent enough to still be active.
    """
    groups: defaultdict[tuple[str, int | None], list[ExpenseRecord]] = defaultdict(list)
    keys: dict[str, str] = {}  # descriptions repeat; normalise each distinct one once
    for record in records:
        key = keys.get(record.description)
        if key is None:
            key = keys[record.description] = normalize_name(record.description)
        if key:
            groups[(key, record.category_id)].append(record)

    found = []
    for (_, category_id), items in groups.items():
        items.sort(key=lambda r: r.day)
        if len(items) < RECURRING_MIN_OCCURRENCES:
            continue
        gaps = [(b.day - a.day).days for a, b in pairwise(items)]
        if min(gaps) == 0:
            continue
        typical_gap = _median(gaps)
        cadence = next(
            (c for c, (low, high) in _CADENCE_GAP_DAYS.items() if low <= typical_gap <= high),
            None,
        )
        if cadence is None or any(
            abs(gap - typical_gap) > typical_gap * _GAP_TOLERANCE for gap in gaps
        ):
            continue
        amounts = [r.amount_minor for r in items]
        if max(amounts) > min(amounts) * _MAX_AMOUNT_SPREAD:
            continue
        last = items[-1].day
        if Decimal((as_of - last).days) > typical_gap * _OVERDUE_FACTOR:
            continue

        typical_minor = int(_median(amounts).quantize(Decimal(1), rounding=ROUND_HALF_UP))
        monthly_minor = (
            typical_minor
            if cadence is Cadence.MONTHLY
            else int((typical_minor * _WEEKS_PER_MONTH).quantize(Decimal(1), rounding=ROUND_HALF_UP))
        )
        gap_days = int(typical_gap.quantize(Decimal(1), rounding=ROUND_HALF_UP))
        found.append(
            RecurringExpense(
                label=items[-1].description.strip(),
                category_id=category_id,
                cadence=cadence,
                typical_amount=Money.from_minor_units(typical_minor, currency),
                occurrences=len(items),
                first_seen=items[0].day,
                last_seen=last,
                next_expected=last + timedelta(days=gap_days),
                monthly_cost=Money.from_minor_units(monthly_minor, currency),
                is_fixed_amount=min(amounts) == max(amounts),
            )
        )
    found.sort(key=lambda r: (-r.monthly_cost.minor_units, r.label.casefold()))
    return tuple(found)


# ---------------------------------------------------------------- helpers


def _median(values: Sequence[int]) -> Decimal:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return Decimal(ordered[middle])
    return (Decimal(ordered[middle - 1]) + Decimal(ordered[middle])) / 2


def _name(names: Mapping[int, str], category_id: int | None) -> str:
    return tr("Uncategorised") if category_id is None else names.get(category_id, "?")
