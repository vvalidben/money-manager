"""Turns a ``DashboardOverview`` into display text (pure presentation, no Qt).

No figures are computed here: every amount, ratio and health judgement comes
from the service/domain; this module only chooses words and formats.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from money_manager.domain.dashboard import DashboardOverview
from money_manager.domain.health import HealthLevel
from money_manager.ui.formatting import (
    format_date,
    format_day_range,
    format_money,
    format_month,
    format_percent,
    format_signed_money,
)

Tone = Literal["neutral", "inflow", "outflow"]

LEVEL_TEXT = {
    HealthLevel.GOOD: "✓ Good",
    HealthLevel.FAIR: "● Fair",
    HealthLevel.POOR: "! Needs attention",
    HealthLevel.UNKNOWN: "– Not enough data",
}


@dataclass(frozen=True, slots=True)
class StatView:
    label: str
    value: str
    caption: str
    tone: Tone = "neutral"


@dataclass(frozen=True, slots=True)
class AllocationRowView:
    name: str
    amount: str
    share: str
    bar_fraction: Decimal  # 0..1, only for drawing the share bar
    is_available: bool
    is_negative: bool


@dataclass(frozen=True, slots=True)
class HealthRowView:
    label: str
    value: str
    detail: str
    level: HealthLevel | None  # None = informational, not judged
    level_text: str


@dataclass(frozen=True, slots=True)
class DashboardView:
    subtitle: str
    stats: tuple[StatView, ...]
    allocation_rows: tuple[AllocationRowView, ...]
    allocation_note: str | None
    health_rows: tuple[HealthRowView, ...]


def build_dashboard_view(overview: DashboardOverview) -> DashboardView:
    period = overview.period
    period_text = format_day_range(period.start, period.end)
    return DashboardView(
        subtitle=f"{format_month(period.end)} · month to date ({period_text})",
        stats=_stats(overview, period_text),
        allocation_rows=_allocation_rows(overview),
        allocation_note=_allocation_note(overview),
        health_rows=_health_rows(overview),
    )


def _stats(overview: DashboardOverview, period_text: str) -> tuple[StatView, ...]:
    health = overview.health
    net = overview.savings
    if overview.income.is_positive() and health.savings_rate is not None:
        net_caption = f"{format_percent(health.savings_rate)} of income"
    else:
        net_caption = "No income recorded yet this month"
    previous = overview.previous_period
    return (
        _balance_stat(overview),
        StatView(
            "Income this month",
            format_signed_money(overview.income),
            period_text,
            "inflow",
        ),
        StatView(
            "Expenses this month",
            format_signed_money(-overview.expenses),
            f"vs {format_money(overview.previous_period_expenses)} in "
            f"{format_day_range(previous.start, previous.end)}",
            "outflow",
        ),
        StatView(
            "Saved this month" if not net.is_negative() else "Overspent this month",
            format_signed_money(net),
            net_caption,
            "outflow" if net.is_negative() else "inflow",
        ),
    )


def _balance_stat(overview: DashboardOverview) -> StatView:
    """The headline balance leaves out money set aside for goals (and other allocations)."""
    summary = overview.allocation
    available, set_aside = summary.available, summary.allocated_total
    if set_aside.is_positive():
        goal_allocations = {g.goal.allocation_id for g in overview.goals}
        only_goals = all(row.allocation.id in goal_allocations
                         for row in summary.allocations if row.balance.is_positive())
        where = "in goals" if only_goals else "set aside"
        caption = f"{format_money(overview.total_balance)} total − {format_money(set_aside)} {where}"
    else:
        caption = f"Nothing set aside · as of {format_date(overview.period.end)}"
    return StatView("Available balance", format_money(available), caption,
                    "outflow" if available.is_negative() else "neutral")


def _allocation_rows(overview: DashboardOverview) -> tuple[AllocationRowView, ...]:
    rows = []
    for item in overview.allocation_slices:
        share = item.share
        rows.append(
            AllocationRowView(
                name=item.name,
                amount=format_money(item.amount),
                share="—" if share is None else format_percent(share),
                bar_fraction=min(max(share or Decimal(0), Decimal(0)), Decimal(1)),
                is_available=item.allocation_id is None,
                is_negative=item.amount.is_negative(),
            )
        )
    return tuple(rows)


def _allocation_note(overview: DashboardOverview) -> str | None:
    summary = overview.allocation
    if summary.is_over_allocated:
        return (
            f"Over-allocated by {format_money(summary.shortfall)}: allocations exceed your "
            "real balance. Move money from an allocation back to Available."
        )
    if not summary.allocations:
        return "No allocations yet — all of your money is Available."
    return None


def _health_rows(overview: DashboardOverview) -> tuple[HealthRowView, ...]:
    health = overview.health
    previous, period = overview.previous_period, overview.period
    return (
        HealthRowView(
            "Savings rate",
            "—" if health.savings_rate is None else format_percent(health.savings_rate),
            "Share of this month's income you kept",
            health.savings_level,
            LEVEL_TEXT[health.savings_level],
        ),
        HealthRowView(
            "Spending vs last month",
            "—"
            if health.spending_change is None
            else format_percent(health.spending_change, signed=True),
            f"{format_day_range(period.start, period.end)} vs "
            f"{format_day_range(previous.start, previous.end)}",
            health.spending_level,
            LEVEL_TEXT[health.spending_level],
        ),
        HealthRowView(
            "Emergency runway",
            "—" if health.runway_months is None else f"{health.runway_months} months",
            "Balance ÷ average monthly spending (last 3 full months)",
            health.runway_level,
            LEVEL_TEXT[health.runway_level],
        ),
        HealthRowView(
            "Allocated",
            "—" if health.allocated_share is None else format_percent(health.allocated_share),
            "Share of your balance set aside in allocations",
            None,
            "",
        ),
    )
