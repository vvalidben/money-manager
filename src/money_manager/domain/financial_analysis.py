"""Deterministic financial-health analysis (no AI, no judgements).

Everything here is computed from recorded data with exact ``Decimal``
arithmetic and fixed, documented rules, and every conclusion is phrased as a
measurable fact ("Expenses increased by 18.0% compared with …"). A later AI
feature may *interpret* these facts; it never computes them.

Definitions (in addition to ``domain.analytics``)
------------------------------------------------
* Spending ratio = spending ÷ income; savings rate = savings ÷ income;
  investment rate = investments ÷ income (all undefined without income).
* Comparison period: a whole calendar month is compared with the whole
  previous month; a month-to-date period starting on the 1st with the same
  days of the previous month; any other period with the equally long period
  immediately before it.
* Trends use the last ``TREND_MONTHS`` *complete* months since tracking
  began, comparing the average of the newer half with the older half:
  within ±5 % = stable. Fewer than two months = not enough data.
* Unusual spending (investment categories excluded; needs history):
  - category spike: spending ≥ 1.5 × its average over the previous 3 equal
    periods, and the increase ≥ 5 % of this period's spending;
  - new category: no spending in the previous 3 periods and ≥ 10 % of this
    period's spending;
  - large expense: a single expense ≥ 3 × the median expense *of its own
    category* in the previous 3 periods (at least 3 of them) and ≥ 10 % of
    this period's spending.
  Only earlier periods lying entirely after tracking began are used.
* Comparisons (income/expense/category changes) are only made when the
  comparison period lies entirely after tracking began; otherwise they are
  reported as unavailable rather than as a misleading percentage.
"""

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from money_manager.domain.analytics import (
    CategoryAmount,
    CategoryChange,
    ExpenseRecord,
    LedgerEntry,
    MonthSummary,
    PeriodTotals,
    RecurringExpense,
    TrendDirection,
)
from money_manager.domain.enums import TransactionType
from money_manager.domain.health import RATIO_QUANTUM, ratio, relative_change
from money_manager.domain.money import Money, sum_money
from money_manager.domain.periods import (
    DateRange,
    add_months,
    month_end,
    month_start,
    previous_range,
    same_days_previous_month,
)
from money_manager.domain.validation import normalize_name
from money_manager.core.i18n import tr

TREND_MONTHS = 6
STABLE_BAND = Decimal("0.05")
BASELINE_PERIODS = 3
SPIKE_RATIO = Decimal("1.5")
SPIKE_MIN_SHARE = Decimal("0.05")
NEW_CATEGORY_MIN_SHARE = Decimal("0.10")
LARGE_EXPENSE_FACTOR = 3
LARGE_EXPENSE_MIN_SHARE = Decimal("0.10")
LARGE_EXPENSE_MIN_HISTORY = 3  # earlier expenses in the same category
MAX_UNUSUAL_ITEMS = 5
_FACTOR_QUANTUM = Decimal("0.01")


# ---------------------------------------------------------------- periods


def comparison_range(period: DateRange) -> DateRange:
    """What ``period`` is compared with (see module docstring)."""
    within_one_month = (period.start.year, period.start.month) == (period.end.year,
                                                                   period.end.month)
    if period.start.day == 1 and within_one_month:
        if period.end == month_end(period.end):  # a whole month: the whole previous month
            previous = add_months(period.start, -1)
            return DateRange(previous, month_end(previous))
        return same_days_previous_month(period.end)
    return previous_range(period)


def baseline_ranges(period: DateRange, count: int = BASELINE_PERIODS) -> tuple[DateRange, ...]:
    """The ``count`` equally long ranges immediately before ``period``, newest first."""
    ranges = []
    current = period
    for _ in range(count):
        current = previous_range(current)
        ranges.append(current)
    return tuple(ranges)


def trend_months(period_end: date, tracking_start: date | None) -> tuple[date, ...]:
    """First days of the last ``TREND_MONTHS`` complete months up to ``period_end``."""
    last_complete = (
        month_start(period_end) if month_end(period_end) == period_end
        else add_months(period_end, -1)
    )
    months = [add_months(last_complete, -offset) for offset in range(TREND_MONTHS - 1, -1, -1)]
    if tracking_start is None:
        return ()
    first_tracked = month_start(tracking_start)
    return tuple(m for m in months if m >= first_tracked)


# ----------------------------------------------------------------- trends


@dataclass(frozen=True, slots=True)
class MonthValue:
    month: date
    value: Money


@dataclass(frozen=True, slots=True)
class MetricTrend:
    """A monthly series and its direction (newer half vs older half)."""

    series: tuple[MonthValue, ...]
    direction: TrendDirection
    change: Decimal | None  # relative change of the halves' averages


def trend_of(series: Sequence[MonthValue]) -> MetricTrend:
    if len(series) < 2:
        return MetricTrend(tuple(series), TrendDirection.NO_DATA, None)
    half = len(series) // 2
    older = [v.value.amount for v in series[:half]]
    newer = [v.value.amount for v in series[-half:]]
    older_avg = sum(older, Decimal(0)) / len(older)
    newer_avg = sum(newer, Decimal(0)) / len(newer)
    if older_avg == 0:
        if newer_avg == 0:
            return MetricTrend(tuple(series), TrendDirection.STABLE, Decimal(0))
        direction = TrendDirection.RISING if newer_avg > 0 else TrendDirection.FALLING
        return MetricTrend(tuple(series), direction, None)
    change = ((newer_avg - older_avg) / abs(older_avg)).quantize(
        RATIO_QUANTUM, rounding=ROUND_HALF_UP)
    if abs(change) <= STABLE_BAND:
        direction = TrendDirection.STABLE
    else:
        direction = TrendDirection.RISING if change > 0 else TrendDirection.FALLING
    return MetricTrend(tuple(series), direction, change)


def month_end_balances(
    changes: Mapping[date, int], months: Sequence[date], currency: str
) -> tuple[MonthValue, ...]:
    """Total balance at the end of each month."""
    ordered = sorted(changes.items())
    result = []
    for month in months:
        end = month_end(month)
        total = sum(amount for day, amount in ordered if day <= end)
        result.append(MonthValue(month, Money.from_minor_units(total, currency)))
    return tuple(result)


# ----------------------------------------------------------------- unusual


class UnusualKind(StrEnum):
    CATEGORY_SPIKE = "category_spike"
    NEW_CATEGORY = "new_category"
    LARGE_EXPENSE = "large_expense"


@dataclass(frozen=True, slots=True)
class UnusualSpending:
    kind: UnusualKind
    category_id: int | None
    category_name: str
    amount: Money  # this period's category spending, or the single expense
    baseline: Money  # average per previous period, or the median expense
    factor: Decimal | None  # amount ÷ baseline (None for new categories)
    day: date | None = None  # large expenses only
    description: str = ""  # large expenses only (free text: not exported by default)


def _category_spending(entries: Iterable[LedgerEntry], period: DateRange,
                       investment_ids: frozenset[int]) -> dict[int | None, int]:
    totals: defaultdict[int | None, int] = defaultdict(int)
    for entry in entries:
        if (entry.type is TransactionType.EXPENSE and entry.day in period
                and entry.category_id not in investment_ids):
            totals[entry.category_id] += entry.amount_minor
    return dict(totals)


def detect_unusual_spending(
    entries: Sequence[LedgerEntry],
    records: Sequence[ExpenseRecord],
    period: DateRange,
    names: Mapping[int, str],
    investment_ids: frozenset[int],
    currency: str,
    tracking_start: date | None,
) -> tuple[UnusualSpending, ...]:
    """Category spikes, large new categories and large single expenses (see module rules).

    Only baseline periods that lie entirely within tracked history count, so a
    period before the first account existed never looks like "no spending".
    """
    if tracking_start is None:
        return ()
    baselines = tuple(b for b in baseline_ranges(period) if b.start >= tracking_start)
    if not baselines:
        return ()
    current = _category_spending(entries, period, investment_ids)
    period_spending = sum(current.values())
    if period_spending <= 0:
        return ()
    history = [_category_spending(entries, r, investment_ids) for r in baselines]
    history_total = sum(sum(h.values()) for h in history)
    if history_total <= 0:
        return ()  # no earlier spending recorded: nothing to compare with

    def money(minor: int | Decimal) -> Money:
        value = Decimal(minor) if isinstance(minor, int) else minor
        return Money.from_minor_units(int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP)),
                                      currency)

    def name(category_id: int | None) -> str:
        return tr("Uncategorised") if category_id is None else names.get(category_id, "?")

    found: list[UnusualSpending] = []
    for category_id, amount in current.items():
        average = Decimal(sum(h.get(category_id, 0) for h in history)) / len(history)
        if average == 0:
            if Decimal(amount) >= period_spending * NEW_CATEGORY_MIN_SHARE:
                found.append(UnusualSpending(UnusualKind.NEW_CATEGORY, category_id,
                                             name(category_id), money(amount), money(0), None))
            continue
        increase = Decimal(amount) - average
        if (Decimal(amount) >= average * SPIKE_RATIO
                and increase >= period_spending * SPIKE_MIN_SHARE):
            found.append(UnusualSpending(
                UnusualKind.CATEGORY_SPIKE, category_id, name(category_id), money(amount),
                money(average), (Decimal(amount) / average).quantize(
                    _FACTOR_QUANTUM, rounding=ROUND_HALF_UP)))

    # A single expense is compared with the typical expense of its own category,
    # so a regular large bill (e.g. rent) is never flagged. The baseline periods
    # are consecutive, so together they form one date range.
    history_span = DateRange(baselines[-1].start, baselines[0].end)
    by_category: defaultdict[int | None, list[int]] = defaultdict(list)
    for r in records:
        if r.category_id not in investment_ids and r.day in history_span:
            by_category[r.category_id].append(r.amount_minor)
    medians = {category_id: _median(sorted(amounts))
               for category_id, amounts in by_category.items()
               if len(amounts) >= LARGE_EXPENSE_MIN_HISTORY}
    for r in records:
        median = medians.get(r.category_id)
        if median is None or r.day not in period or r.category_id in investment_ids:
            continue
        if (Decimal(r.amount_minor) >= median * LARGE_EXPENSE_FACTOR
                and Decimal(r.amount_minor) >= period_spending * LARGE_EXPENSE_MIN_SHARE):
            found.append(UnusualSpending(
                UnusualKind.LARGE_EXPENSE, r.category_id, name(r.category_id),
                money(r.amount_minor), money(median),
                (Decimal(r.amount_minor) / median).quantize(_FACTOR_QUANTUM,
                                                            rounding=ROUND_HALF_UP),
                r.day, r.description))

    found.sort(key=lambda u: (-u.amount.minor_units, u.kind.value, u.category_name.casefold()))
    return tuple(found[:MAX_UNUSUAL_ITEMS])


def _median(values: Sequence[int]) -> Decimal:
    middle = len(values) // 2
    if len(values) % 2:
        return Decimal(values[middle])
    return (Decimal(values[middle - 1]) + Decimal(values[middle])) / 2


# --------------------------------------------------------------- recurring


@dataclass(frozen=True, slots=True)
class RecurringAnalysis:
    detected: tuple[RecurringExpense, ...]
    detected_monthly_total: Money
    subscriptions_monthly_total: Money  # active subscriptions the user declared
    untracked: tuple[RecurringExpense, ...]  # detected but not declared as subscriptions
    share_of_monthly_spending: Decimal | None  # detected total ÷ average monthly spending


def recurring_analysis(
    detected: Sequence[RecurringExpense],
    subscription_names: Iterable[str],
    subscriptions_monthly_total: Money,
    average_monthly_spending: Money | None,
) -> RecurringAnalysis:
    declared = {normalize_name(n) for n in subscription_names}
    currency = subscriptions_monthly_total.currency
    total = sum_money((r.monthly_cost for r in detected), currency)
    return RecurringAnalysis(
        detected=tuple(detected),
        detected_monthly_total=total,
        subscriptions_monthly_total=subscriptions_monthly_total,
        untracked=tuple(r for r in detected if normalize_name(r.label) not in declared),
        share_of_monthly_spending=(
            ratio(total, average_monthly_spending)
            if average_monthly_spending is not None and average_monthly_spending.is_positive()
            else None
        ),
    )


# ---------------------------------------------------------------- analysis


@dataclass(frozen=True, slots=True)
class Fact:
    """One measurable statement, with the figures it is based on."""

    code: str
    text: str
    data: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FinancialAnalysis:
    period: DateRange
    comparison_period: DateRange
    has_accounts: bool
    current_balance: Money  # at the end of the period
    totals: PeriodTotals
    comparison_totals: PeriodTotals
    spending_by_category: tuple[CategoryAmount, ...]
    category_changes: tuple[CategoryChange, ...]
    monthly: tuple[MonthSummary, ...]
    income_trend: MetricTrend
    expense_trend: MetricTrend  # spending, i.e. expenses excluding investments
    balance_trend: MetricTrend
    unusual_spending: tuple[UnusualSpending, ...]
    recurring: RecurringAnalysis
    comparison_complete: bool = True  # the comparison period lies within tracked history
    tracking_start: date | None = None
    facts: tuple[Fact, ...] = ()

    # Headline figures, named as in the requirements.
    @property
    def period_income(self) -> Money:
        return self.totals.income

    @property
    def period_expenses(self) -> Money:
        return self.totals.expenses

    @property
    def net_change(self) -> Money:
        return self.totals.net_change

    @property
    def savings_amount(self) -> Money:
        return self.totals.savings

    @property
    def savings_rate(self) -> Decimal | None:
        return self.totals.savings_rate

    @property
    def investment_amount(self) -> Money:
        return self.totals.investments

    @property
    def investment_rate(self) -> Decimal | None:
        return self.totals.investment_rate

    @property
    def spending_ratio(self) -> Decimal | None:
        """Spending ÷ income (above 1 = spent more than earned)."""
        if not self.totals.income.is_positive():
            return None
        return ratio(self.totals.spending, self.totals.income)

    @property
    def largest_expense_category(self) -> CategoryAmount | None:
        return self.spending_by_category[0] if self.spending_by_category else None

    @property
    def income_change(self) -> Decimal | None:
        if not self.comparison_complete:
            return None
        return relative_change(self.totals.income, self.comparison_totals.income)

    @property
    def expenses_change(self) -> Decimal | None:
        if not self.comparison_complete:
            return None
        return relative_change(self.totals.expenses, self.comparison_totals.expenses)

    @property
    def spending_change(self) -> Decimal | None:
        if not self.comparison_complete:
            return None
        return relative_change(self.totals.spending, self.comparison_totals.spending)


# ------------------------------------------------------------------ facts


def money_text(value: Money) -> str:
    return str(value)


def percent_text(fraction: Decimal, *, signed: bool = False) -> str:
    percent = (fraction * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    sign = "+" if signed and percent > 0 else ""
    return f"{sign}{percent}%"


def range_text(period: DateRange) -> str:
    return f"{period.start.isoformat()} to {period.end.isoformat()}"


def _change_fact(code: str, label: str, current: Money, previous: Money,
                 comparison: DateRange, *, plural: bool) -> Fact | None:
    change = relative_change(current, previous)
    data = {"current": str(current.amount), "previous": str(previous.amount),
            "comparison_period": range_text(comparison)}
    if change is None:
        if current.is_zero():
            return None
        return Fact(code, tr("{0}: {1}; nothing recorded in the comparison period ({2}).", label, money_text(current), range_text(comparison)), data)
    data["change"] = str(change)
    if change == 0:
        verb = tr("were unchanged") if plural else tr("was unchanged")
        detail = ""
    else:
        verb = "increased" if change > 0 else "decreased"
        verb = f"{verb} by {percent_text(abs(change))}"
        detail = f" ({money_text(previous)} -> {money_text(current)})"
    return Fact(code, tr("{0} {1} compared with {2}{3}.", label, verb, range_text(comparison), detail), data)


def _trend_fact(code: str, label: str, trend: MetricTrend) -> Fact | None:
    if trend.direction is TrendDirection.NO_DATA:
        return None
    months = len(trend.series)
    data = {"direction": trend.direction.value, "months": str(months)}
    text = tr("{0} over the last {1} complete months: {2}", label, months, trend.direction.value)
    if trend.change is not None:
        data["change"] = str(trend.change)
        text += tr(" ({0}, newer vs older half)", percent_text(trend.change, signed=True))
    return Fact(code, text + ".", data)


def build_facts(analysis: FinancialAnalysis) -> tuple[Fact, ...]:
    """Neutral, measurable statements; a fact is left out when its data is missing."""
    totals, period = analysis.totals, analysis.period
    facts: list[Fact | None] = [
        Fact("balance", tr("Balance on {0}: {1}.", period.end.isoformat(), money_text(analysis.current_balance)),
             {"balance": str(analysis.current_balance.amount)}),
        Fact("net_change", tr("The balance changed by {0}{1} from {2}.", '+' if totals.net_change.is_positive() else '', money_text(totals.net_change), range_text(period)),
             {"net_change": str(totals.net_change.amount)}),
    ]
    if analysis.comparison_complete:
        facts += [
            _change_fact("income_change", tr("Income"), totals.income,
                         analysis.comparison_totals.income, analysis.comparison_period,
                         plural=False),
            _change_fact("expenses_change", tr("Expenses"), totals.expenses,
                         analysis.comparison_totals.expenses, analysis.comparison_period,
                         plural=True),
        ]
    elif analysis.tracking_start is not None:
        facts.append(Fact(
            "comparison_unavailable",
            tr("No comparison: the comparison period ({0}) starts before tracking began "
               "on {1}.", range_text(analysis.comparison_period), analysis.tracking_start.isoformat()),
            {"comparison_period": range_text(analysis.comparison_period),
             "tracking_start": analysis.tracking_start.isoformat()}))
    if analysis.spending_ratio is not None:
        facts.append(Fact("spending_ratio",
                          tr("Spending was {0} of income.", percent_text(analysis.spending_ratio)),
                          {"spending_ratio": str(analysis.spending_ratio)}))
    elif totals.spending.is_positive():
        facts.append(Fact("no_income", tr("No income was recorded while spending was {0}.", money_text(totals.spending)),
                          {"spending": str(totals.spending.amount)}))
    if analysis.savings_rate is not None:
        facts.append(Fact("savings_rate",
                          tr("Savings were {0}, {1} of income.", money_text(totals.savings), percent_text(analysis.savings_rate)),
                          {"savings": str(totals.savings.amount),
                           "savings_rate": str(analysis.savings_rate)}))
    if analysis.investment_rate is not None and totals.investments.is_positive():
        facts.append(Fact("investment_rate",
                          tr("Investment contributions were {0}, {1} of income.", money_text(totals.investments), percent_text(analysis.investment_rate)),
                          {"investments": str(totals.investments.amount),
                           "investment_rate": str(analysis.investment_rate)}))
    largest = analysis.largest_expense_category
    if largest is not None and largest.share is not None:
        facts.append(Fact("largest_category",
                          tr("Largest spending category: {0}, {1} ({2} of spending).", largest.name, money_text(largest.amount), percent_text(largest.share)),
                          {"category": largest.name, "amount": str(largest.amount.amount),
                           "share": str(largest.share)}))
    for change in (analysis.category_changes[:3] if analysis.comparison_complete else ()):
        if change.is_new:
            facts.append(Fact("category_new",
                              tr("{0}: {1}, with no spending in the comparison period.", change.name, money_text(change.current)),
                              {"category": change.name, "current": str(change.current.amount)}))
        elif change.change_ratio is not None and change.change_ratio != 0:
            verb = "increased" if change.change_ratio > 0 else "decreased"
            facts.append(Fact("category_change",
                              f"{change.name} spending {verb} by "
                              f"{percent_text(abs(change.change_ratio))} "
                              f"({money_text(change.previous)} -> {money_text(change.current)}).",
                              {"category": change.name, "previous": str(change.previous.amount),
                               "current": str(change.current.amount),
                               "change": str(change.change_ratio)}))
    for item in analysis.unusual_spending:
        facts.append(_unusual_fact(item))
    recurring = analysis.recurring
    if recurring.detected:
        share = ("" if recurring.share_of_monthly_spending is None else
                 tr(" ({0} of average monthly spending)", percent_text(recurring.share_of_monthly_spending)))
        facts.append(Fact("recurring",
                          tr("{0} recurring expenses detected, about {1} per month{2}; {3} not "
                             "tracked as subscriptions.", len(recurring.detected), money_text(recurring.detected_monthly_total), share, len(recurring.untracked)),
                          {"count": str(len(recurring.detected)),
                           "monthly_total": str(recurring.detected_monthly_total.amount),
                           "untracked": str(len(recurring.untracked))}))
    facts.extend([
        _trend_fact("income_trend", tr("Income"), analysis.income_trend),
        _trend_fact("expense_trend", tr("Spending"), analysis.expense_trend),
        _trend_fact("balance_trend", tr("Month-end balance"), analysis.balance_trend),
    ])
    return tuple(f for f in facts if f is not None)


def _unusual_fact(item: UnusualSpending) -> Fact:
    data = {"kind": item.kind.value, "category": item.category_name,
            "amount": str(item.amount.amount), "baseline": str(item.baseline.amount)}
    if item.factor is not None:
        data["factor"] = str(item.factor)
    match item.kind:
        case UnusualKind.CATEGORY_SPIKE:
            text = (tr("{0} spending of {1} is {2}x its average of {3} over the previous {4} "
                       "periods.", item.category_name, money_text(item.amount), item.factor, money_text(item.baseline), BASELINE_PERIODS))
        case UnusualKind.NEW_CATEGORY:
            text = (tr("{0} spending of {1} has no history in the previous {2} periods.", item.category_name, money_text(item.amount), BASELINE_PERIODS))
        case UnusualKind.LARGE_EXPENSE:
            assert item.day is not None
            data["date"] = item.day.isoformat()
            text = (tr("A single {0} expense of {1} on {2} is {3}x the typical expense of {4}.", item.category_name, money_text(item.amount), item.day.isoformat(), item.factor, money_text(item.baseline)))
    return Fact("unusual_" + item.kind.value, text, data)
