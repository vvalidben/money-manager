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

MONTH_HEADERS = ("Month", "Income", "Expenses", "Invested", "Saved", "Savings rate",
                 "Spending vs prev.")
RECURRING_HEADERS = ("Expense", "Category", "Every", "Typical amount", "Per month",
                     "Last paid", "Next expected")
CADENCE_TEXT = {Cadence.WEEKLY: "Week", Cadence.MONTHLY: "Month"}


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
                     f"({period.days} {'day' if period.days == 1 else 'days'})",
        comparison_label=(
            f"Changes compare with {format_date(previous.start)} – {format_date(previous.end)}"
            if report.comparison_complete
            else f"No comparison: {format_date(previous.start)} – {format_date(previous.end)} "
                 "is before tracking began"
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
            f"About {format_money(report.recurring_monthly_total)} per month in "
            f"{len(report.recurring)} recurring {'expense' if len(report.recurring) == 1 else 'expenses'}"
            " (detected from the last 12 months)"
            if report.recurring
            else "No regular weekly or monthly expenses detected in the last 12 months."
        ),
    )


def change_caption(change: Decimal | None, comparable: bool = True) -> str:
    if not comparable:
        return "Previous period is before tracking began"
    if change is None:
        return "Nothing to compare with in the previous period"
    return f"{format_percent(change, signed=True)} vs previous period"


def _stats(report: StatisticsReport) -> tuple[StatView, ...]:
    totals = report.totals
    savings = totals.savings
    if totals.savings_rate is not None:
        savings_caption = f"Savings rate {format_percent(totals.savings_rate)}"
    else:
        savings_caption = "No income in this period"
    if not report.has_investment_categories:
        invest_caption = "Mark investment categories to track this"
    elif totals.investment_rate is None:
        invest_caption = "No income in this period"
    else:
        invest_caption = f"Investment rate {format_percent(totals.investment_rate)} of income"
    return (
        StatView("Income", format_signed_money(totals.income),
                 change_caption(report.income_change, report.comparison_complete), "inflow"),
        StatView("Expenses", format_signed_money(-totals.expenses),
                 change_caption(report.expenses_change, report.comparison_complete), "outflow"),
        StatView("Saved" if not savings.is_negative() else "Overspent",
                 format_signed_money(savings), savings_caption,
                 "outflow" if savings.is_negative() else "inflow"),
        StatView("Invested", format_money(totals.investments), invest_caption, "neutral"),
        StatView("Net change", format_signed_money(totals.net_change),
                 f"Balance now {format_money(report.balance.closing)}",
                 "outflow" if totals.net_change.is_negative() else "neutral"),
    )


def _trend_caption(report: StatisticsReport) -> str:
    trend = report.trend
    average = f"Average {format_money(trend.average_per_day)} per day"
    match trend.direction:
        case TrendDirection.NO_DATA:
            return "No spending in this period"
        case TrendDirection.STABLE:
            return f"{average} · stable (second half vs first half of the range)"
        case TrendDirection.RISING if trend.change is None:
            return f"{average} · rising (no spending in the first half)"
        case _:
            word = "rising" if trend.direction is TrendDirection.RISING else "falling"
            assert trend.change is not None
            return (f"{average} · {word} {format_percent(trend.change, signed=True)} "
                    "(second half vs first half of the range)")


def _month_row(report: StatisticsReport, index: int) -> tuple[str, ...]:
    summary = report.months[index]
    totals = summary.totals
    change = summary.spending_change
    return (
        format_month(summary.month) + (" (to date)" if summary.is_partial else ""),
        format_money(totals.income),
        format_money(totals.expenses),
        format_money(totals.investments),
        format_signed_money(totals.savings),
        "—" if totals.savings_rate is None else format_percent(totals.savings_rate),
        "—" if change is None else format_percent(change, signed=True),
    )
