"""Turns a ``DashboardOverview`` into display text (pure presentation, no Qt).

No figures are computed here: every amount, ratio and health judgement comes
from the service/domain; this module only chooses words and formats.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from money_manager.domain.dashboard import DashboardOverview
from money_manager.domain.health import HealthLevel
from money_manager.domain.subscriptions import UpcomingPayment
from money_manager.ui.formatting import (
    format_date,
    format_day_range,
    format_money,
    format_month,
    format_percent,
    format_signed_money,
)
from money_manager.core.i18n import tr

Tone = Literal["neutral", "inflow", "outflow"]

LEVEL_TEXT = {
    HealthLevel.GOOD: tr("✓ Good"),
    HealthLevel.FAIR: tr("● Fair"),
    HealthLevel.POOR: tr("! Needs attention"),
    HealthLevel.UNKNOWN: tr("– Not enough data"),
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
        subtitle=tr("{0} · month to date ({1})", format_month(period.end), period_text),
        stats=_stats(overview, period_text),
        allocation_rows=_allocation_rows(overview),
        allocation_note=_allocation_note(overview),
        health_rows=_health_rows(overview),
    )


def _stats(overview: DashboardOverview, period_text: str) -> tuple[StatView, ...]:
    health = overview.health
    net = overview.savings
    if overview.income.is_positive() and health.savings_rate is not None:
        net_caption = tr("{0} of income", format_percent(health.savings_rate))
    else:
        net_caption = tr("No income recorded yet this month")
    previous = overview.previous_period
    return (
        _balance_stat(overview),
        StatView(
            tr("Income this month"),
            format_signed_money(overview.income),
            period_text,
            "inflow",
        ),
        StatView(
            tr("Expenses this month"),
            format_signed_money(-overview.expenses),
            tr("vs {0} in {1}", format_money(overview.previous_period_expenses), format_day_range(previous.start, previous.end)),
            "outflow",
        ),
        StatView(
            tr("Saved this month") if not net.is_negative() else tr("Overspent this month"),
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
        where = tr("in goals") if only_goals else tr("set aside")
        caption = tr("{0} total − {1} {2}", format_money(overview.total_balance), format_money(set_aside), where)
    else:
        caption = tr("Nothing set aside · as of {0}", format_date(overview.period.end))
    return StatView(tr("Available balance"), format_money(available), caption,
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
            tr("Over-allocated by {0}: allocations exceed your real balance. Move money "
               "from an allocation back to Available.", format_money(summary.shortfall))
        )
    if not summary.allocations:
        return tr("No allocations yet — all of your money is Available.")
    return None


def _health_rows(overview: DashboardOverview) -> tuple[HealthRowView, ...]:
    health = overview.health
    previous, period = overview.previous_period, overview.period
    return (
        HealthRowView(
            tr("Savings rate"),
            "—" if health.savings_rate is None else format_percent(health.savings_rate),
            tr("Share of this month's income you kept"),
            health.savings_level,
            LEVEL_TEXT[health.savings_level],
        ),
        HealthRowView(
            tr("Spending vs last month"),
            "—"
            if health.spending_change is None
            else format_percent(health.spending_change, signed=True),
            f"{format_day_range(period.start, period.end)} vs "
            f"{format_day_range(previous.start, previous.end)}",
            health.spending_level,
            LEVEL_TEXT[health.spending_level],
        ),
        HealthRowView(
            tr("Emergency runway"),
            "—" if health.runway_months is None else f"{health.runway_months} months",
            tr("Balance ÷ average monthly spending (last 3 full months)"),
            health.runway_level,
            LEVEL_TEXT[health.runway_level],
        ),
        HealthRowView(
            tr("Allocated"),
            "—" if health.allocated_share is None else format_percent(health.allocated_share),
            tr("Share of your balance set aside in allocations"),
            None,
            "",
        ),
    )


@dataclass(frozen=True, slots=True)
class RenewalView:
    day: str  # day of the month, for the date badge
    name: str
    when: str
    amount: str
    overdue: bool


def renewal_views(payments: Sequence[UpcomingPayment], limit: int = 4) -> tuple[RenewalView, ...]:
    """The next few subscription payments, soonest first (overdue ones first of all)."""
    return tuple(
        RenewalView(
            day=str(payment.due_date.day),
            name=payment.subscription.name,
            when=_when(payment.days_until),
            amount=format_money(payment.amount),
            overdue=payment.is_overdue,
        )
        for payment in payments[:limit]
    )


def _when(days: int) -> str:
    if days < 0:
        return tr("Overdue by {0} day{1}", -days, '' if days == -1 else 's')
    if days == 0:
        return tr("Today")
    if days == 1:
        return tr("Tomorrow")
    return tr("In {0} days", days)
