"""Turns budget statuses into display text (pure presentation, no Qt).

Every amount and ratio comes from ``domain.budgets``; this module only words it.
"""

from dataclasses import dataclass
from decimal import Decimal

from money_manager.domain.budgets import BudgetLevel, BudgetStatus, BudgetSummary
from money_manager.ui.dashboard.view_model import StatView
from money_manager.ui.formatting import format_money, format_percent

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
        left = f"{format_money(-remaining)} over the limit"
    else:
        left = f"{format_money(remaining)} left this month"
    projected = status.projected
    projection = "" if projected is None else (
        f"At this pace: {format_money(projected)} by the end of the month")
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
        StatView("Planned this month", format_money(summary.planned),
                 f"{count} budget{'' if count == 1 else 's'}"),
        StatView("Spent so far", format_money(summary.spent), "In budgeted categories"),
        StatView("Over budget" if remaining.is_negative() else "Left to spend",
                 format_money(-remaining if remaining.is_negative() else remaining),
                 "Across all budgets", "outflow" if remaining.is_negative() else "inflow"),
        StatView("Over the limit", str(summary.over_count),
                 "Everything within its limit" if summary.over_count == 0
                 else f"categor{'y' if summary.over_count == 1 else 'ies'} over budget"),
    )
