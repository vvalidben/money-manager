"""Turns a ``StatisticsReport`` into display text (pure presentation, no Qt).

No figures are computed here: every amount, ratio and trend comes from the
deterministic analytics engine; this module only chooses words and formats.
"""

from dataclasses import dataclass
from decimal import Decimal

from money_manager.domain.analytics import Cadence, TrendDirection
from money_manager.domain.statistics import StatisticsReport
from money_manager.ui.dashboard.view_model import StatView
from money_manager.ui.formatting import (
    format_date,
    format_money,
    format_month,
    format_percent,
    format_signed_money,
)
from money_manager.core.i18n import tr

MONTH_HEADERS = (tr("Month"), tr("Income"), tr("Expenses"), tr("Invested"), tr("Saved"), tr("Savings rate"),
                 tr("Spending vs prev."))
RECURRING_HEADERS = (tr("Expense"), tr("Category"), tr("Every"), tr("Typical amount"), tr("Per month"),
                     tr("Last paid"), tr("Next expected"))
CADENCE_TEXT = {Cadence.WEEKLY: tr("Week"), Cadence.MONTHLY: tr("Month")}


@dataclass(frozen=True, slots=True)
class StatisticsView:
    period_label: str
    comparison_label: str
    stats: tuple[StatView, ...]
    balance_caption: str
    trend_caption: str
    month_rows: tuple[tuple[str, ...], ...]
    recurring_rows: tuple[tuple[str, ...], ...]
    recurring_caption: str


def build_statistics_view(report: StatisticsReport) -> StatisticsView:
    period, previous = report.period, report.previous_period
    return StatisticsView(
        period_label=f"{format_date(period.start)} – {format_date(period.end)} "
                     f"({period.days} {tr('day') if period.days == 1 else tr('days')})",
        comparison_label=(
            tr("Changes compare with {0} – {1}", format_date(previous.start), format_date(previous.end))
            if report.comparison_complete
            else tr("No comparison: {0} – {1} is before tracking began", format_date(previous.start), format_date(previous.end))
        ),
        stats=_stats(report),
        balance_caption=(
            f"{format_money(report.balance.opening)} → {format_money(report.balance.closing)} "
            f"({format_signed_money(report.balance.change)})"
        ),
        trend_caption=_trend_caption(report),
        month_rows=tuple(_month_row(report, index) for index in range(len(report.months))),
        recurring_rows=tuple(
            (
                item.label,
                report.category_names.get(item.category_id, "—") if item.category_id else "—",
                CADENCE_TEXT[item.cadence],
                format_money(item.typical_amount) + ("" if item.is_fixed_amount else " (varies)"),
                format_money(item.monthly_cost),
                format_date(item.last_seen),
                format_date(item.next_expected),
            )
            for item in report.recurring
        ),
        recurring_caption=(
            tr("About {0} per month in {1} {2} (detected from the last 12 months)",
               format_money(report.recurring_monthly_total), len(report.recurring),
               tr("recurring expense") if len(report.recurring) == 1
               else tr("recurring expenses"))
            if report.recurring
            else tr("No regular weekly or monthly expenses detected in the last 12 months.")
        ),
    )


def change_caption(change: Decimal | None, comparable: bool = True) -> str:
    if not comparable:
        return tr("Previous period is before tracking began")
    if change is None:
        return tr("Nothing to compare with in the previous period")
    return tr("{0} vs previous period", format_percent(change, signed=True))


def _stats(report: StatisticsReport) -> tuple[StatView, ...]:
    totals = report.totals
    savings = totals.savings
    if totals.savings_rate is not None:
        savings_caption = tr("Savings rate {0}", format_percent(totals.savings_rate))
    else:
        savings_caption = tr("No income in this period")
    if not report.has_investment_categories:
        invest_caption = tr("Mark investment categories to track this")
    elif totals.investment_rate is None:
        invest_caption = tr("No income in this period")
    else:
        invest_caption = tr("Investment rate {0} of income", format_percent(totals.investment_rate))
    return (
        StatView(tr("Income"), format_signed_money(totals.income),
                 change_caption(report.income_change, report.comparison_complete), "inflow"),
        StatView(tr("Expenses"), format_signed_money(-totals.expenses),
                 change_caption(report.expenses_change, report.comparison_complete), "outflow"),
        StatView(tr("Saved") if not savings.is_negative() else tr("Overspent"),
                 format_signed_money(savings), savings_caption,
                 "outflow" if savings.is_negative() else "inflow"),
        StatView(tr("Invested"), format_money(totals.investments), invest_caption, "neutral"),
        StatView(tr("Net change"), format_signed_money(totals.net_change),
                 tr("Balance now {0}", format_money(report.balance.closing)),
                 "outflow" if totals.net_change.is_negative() else "neutral"),
    )


def _trend_caption(report: StatisticsReport) -> str:
    trend = report.trend
    average = tr("Average {0} per day", format_money(trend.average_per_day))
    match trend.direction:
        case TrendDirection.NO_DATA:
            return tr("No spending in this period")
        case TrendDirection.STABLE:
            return tr("{0} · stable (second half vs first half of the range)", average)
        case TrendDirection.RISING if trend.change is None:
            return tr("{0} · rising (no spending in the first half)", average)
        case _:
            word = tr("rising") if trend.direction is TrendDirection.RISING else tr("falling")
            assert trend.change is not None
            return (tr("{0} · {1} {2} (second half vs first half of the range)", average, word, format_percent(trend.change, signed=True)))


def _month_row(report: StatisticsReport, index: int) -> tuple[str, ...]:
    summary = report.months[index]
    totals = summary.totals
    change = summary.spending_change
    return (
        format_month(summary.month) + (tr(" (to date)") if summary.is_partial else ""),
        format_money(totals.income),
        format_money(totals.expenses),
        format_money(totals.investments),
        format_signed_money(totals.savings),
        "—" if totals.savings_rate is None else format_percent(totals.savings_rate),
        "—" if change is None else format_percent(change, signed=True),
    )
