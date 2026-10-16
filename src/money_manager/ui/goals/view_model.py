"""Display text for goals (pure presentation, no Qt, no calculations)."""

from dataclasses import dataclass
from decimal import Decimal

from money_manager.domain.goals import GoalProgress, GoalsSummary, GoalStatus
from money_manager.ui.dashboard.view_model import StatView
from money_manager.ui.formatting import format_date, format_money, format_percent

STATUS_TEXT = {
    GoalStatus.COMPLETED: "✓ Completed",
    GoalStatus.ON_TRACK: "✓ On track",
    GoalStatus.BEHIND: "! Behind",
    GoalStatus.OVERDUE: "! Overdue",
    GoalStatus.IN_PROGRESS: "● In progress",
}
# Badge colours reuse the health-level styles (good / fair / poor / neutral).
STATUS_LEVEL = {
    GoalStatus.COMPLETED: "good",
    GoalStatus.ON_TRACK: "good",
    GoalStatus.BEHIND: "fair",
    GoalStatus.OVERDUE: "poor",
    GoalStatus.IN_PROGRESS: "unknown",
}


@dataclass(frozen=True, slots=True)
class GoalCardView:
    goal_id: int
    name: str
    description: str
    status_text: str
    status_level: str
    bar_fraction: Decimal
    amounts: str
    percent: str
    remaining: str
    deadline: str
    pace: str
    tracking: str
    is_manual: bool


def goal_card_view(item: GoalProgress) -> GoalCardView:
    goal = item.goal
    return GoalCardView(
        goal_id=goal.id,
        name=goal.name,
        description=goal.description,
        status_text=STATUS_TEXT[item.status],
        status_level=STATUS_LEVEL[item.status],
        bar_fraction=item.bar_fraction,
        amounts=f"{format_money(item.saved)} of {format_money(goal.target)}",
        percent=format_percent(item.progress),
        remaining=(
            "Target reached"
            if item.is_complete
            else f"{format_money(item.remaining)} to go"
        ),
        deadline=_deadline_text(item),
        pace=_pace_text(item),
        tracking=(
            "Tracked manually — not part of your balance"
            if goal.is_manual
            else f"Money kept in the allocation “{item.allocation_name or '?'}”"
        ),
        is_manual=goal.is_manual,
    )


def summary_stats(summary: GoalsSummary) -> tuple[StatView, ...]:
    behind = summary.count(GoalStatus.BEHIND) + summary.count(GoalStatus.OVERDUE)
    overall = summary.overall_progress
    return (
        StatView(
            "Saved towards goals",
            format_money(summary.total_saved),
            f"of {format_money(summary.total_target)}"
            + ("" if overall is None else f" · {format_percent(overall)}"),
        ),
        StatView(
            "Active goals",
            str(len(summary.active)),
            f"{summary.completed_count} completed",
        ),
        StatView(
            "Needed per month",
            format_money(summary.required_per_month),
            "To meet every deadline",
        ),
        StatView(
            "Behind or overdue",
            str(behind),
            "Goals below their expected pace" if behind else "Everything is on schedule",
            "outflow" if behind else "neutral",
        ),
    )


def _deadline_text(item: GoalProgress) -> str:
    deadline, days_left = item.goal.deadline, item.days_left
    if deadline is None or days_left is None:
        return "No deadline"
    due = f"Due {format_date(deadline)}"
    if item.is_complete:
        return due
    if days_left < 0:
        return f"{due} · overdue by {-days_left} {'day' if days_left == -1 else 'days'}"
    if days_left == 0:
        return f"{due} · due today"
    return f"{due} · {days_left} {'day' if days_left == 1 else 'days'} left"


def _pace_text(item: GoalProgress) -> str:
    required = item.required_per_month
    if item.is_complete:
        return "Well done — this goal is fully funded."
    if item.status is GoalStatus.OVERDUE:
        return "The deadline has passed. Edit the goal to set a new one."
    if required is None:
        return "Set a deadline to see how much to save each month."
    return f"Save {format_money(required)} per month to finish on time."
