"""Turns budget statuses into display text (pure presentation, no Qt).

Every amount and ratio comes from ``domain.budgets``; this module only words it.
"""

from dataclasses import dataclass
from decimal import Decimal

from money_manager.domain.budgets import BudgetLevel, BudgetStatus, BudgetSummary
from money_manager.ui.dashboard.view_model import StatView
from money_manager.ui.formatting import format_money, format_percent
from money_manager.core.i18n import tr

# Status chip levels (shared badge styles: good / fair / poor).
CHIP_LEVELS = {BudgetLevel.ON_TRACK: "good", BudgetLevel.NEAR_LIMIT: "fair",
               BudgetLevel.OVER: "poor"}


@dataclass(frozen=True, slots=True)
class BudgetCardView:
    category_id: int
    name: str
    status: str
    chip_level: str
    bar_level: str
    spent: str
    limit: str
    limit_amount: str
    bar_fraction: Decimal  # 0…1, drawing only
    percent: str
    left: str
    projection: str


def budget_card_view(status: BudgetStatus) -> BudgetCardView:
    remaining = status.remaining
    if remaining.is_negative():
        left = tr("{0} over the limit", format_money(-remaining))
    else:
        left = tr("{0} left this month", format_money(remaining))
    projected = status.projected
    projection = "" if projected is None else (
        tr("At this pace: {0} by the end of the month", format_money(projected)))
    return BudgetCardView(
        category_id=status.budget.category_id,
        name=status.category_name,
        status=status.level.label,
        chip_level=CHIP_LEVELS[status.level],
        bar_level=status.level.value,
        spent=format_money(status.spent),
        limit=f"of {format_money(status.budget.limit)}",
        limit_amount=format_money(status.budget.limit),
        bar_fraction=min(max(status.ratio, Decimal(0)), Decimal(1)),
        percent=format_percent(status.ratio),
        left=left,
        projection=projection,
    )


def summary_stats(summary: BudgetSummary) -> tuple[StatView, ...]:
    remaining = summary.remaining
    count = len(summary.statuses)
    return (
        StatView(tr("Planned this month"), format_money(summary.planned),
                 f"{count} budget{'' if count == 1 else 's'}"),
        StatView(tr("Spent so far"), format_money(summary.spent), tr("In budgeted categories")),
        StatView(tr("Over budget") if remaining.is_negative() else tr("Left to spend"),
                 format_money(-remaining if remaining.is_negative() else remaining),
                 tr("Across all budgets"), "outflow" if remaining.is_negative() else "inflow"),
        StatView(tr("Over the limit"), str(summary.over_count),
                 tr("Everything within its limit") if summary.over_count == 0
                 else (tr("category over budget") if summary.over_count == 1
                       else tr("categories over budget"))),
    )
