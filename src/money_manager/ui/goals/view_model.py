"""Display text for goals (pure presentation, no Qt, no calculations)."""

from dataclasses import dataclass
from decimal import Decimal

from money_manager.domain.goals import GoalProgress, GoalsSummary, GoalStatus
from money_manager.ui.dashboard.view_model import StatView
from money_manager.ui.formatting import format_date, format_money, format_percent
from money_manager.core.i18n import tr

STATUS_TEXT = {
    GoalStatus.COMPLETED: tr("✓ Completed"),
    GoalStatus.ON_TRACK: tr("✓ On track"),
    GoalStatus.BEHIND: tr("! Behind"),
    GoalStatus.OVERDUE: tr("! Overdue"),
    GoalStatus.IN_PROGRESS: tr("● In progress"),
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
            tr("Target reached")
            if item.is_complete
            else tr("{0} to go", format_money(item.remaining))
        ),
        deadline=_deadline_text(item),
        pace=_pace_text(item),
        tracking=(
            tr("Tracked manually — not part of your balance")
            if goal.is_manual
            else tr("Money kept in the allocation “{0}”", item.allocation_name or '?')
        ),
        is_manual=goal.is_manual,
    )


def summary_stats(summary: GoalsSummary) -> tuple[StatView, ...]:
    behind = summary.count(GoalStatus.BEHIND) + summary.count(GoalStatus.OVERDUE)
    overall = summary.overall_progress
    return (
        StatView(
            tr("Saved towards goals"),
            format_money(summary.total_saved),
            f"of {format_money(summary.total_target)}"
            + ("" if overall is None else f" · {format_percent(overall)}"),
        ),
        StatView(
            tr("Active goals"),
            str(len(summary.active)),
            f"{summary.completed_count} completed",
        ),
        StatView(
            tr("Needed per month"),
            format_money(summary.required_per_month),
            tr("To meet every deadline"),
        ),
        StatView(
            tr("Behind or overdue"),
            str(behind),
            tr("Goals below their expected pace") if behind else tr("Everything is on schedule"),
            "outflow" if behind else "neutral",
        ),
    )


def _deadline_text(item: GoalProgress) -> str:
    deadline, days_left = item.goal.deadline, item.days_left
    if deadline is None or days_left is None:
        return tr("No deadline")
    due = tr("Due {0}", format_date(deadline))
    if item.is_complete:
        return due
    if days_left < 0:
        return tr("{0} · overdue by {1} {2}", due, -days_left,
                  tr("day") if days_left == -1 else tr("days"))
    if days_left == 0:
        return tr("{0} · due today", due)
    return tr("{0} · {1} {2} left", due, days_left, tr("day") if days_left == 1 else tr("days"))


def _pace_text(item: GoalProgress) -> str:
    required = item.required_per_month
    if item.is_complete:
        return tr("Well done — this goal is fully funded.")
    if item.status is GoalStatus.OVERDUE:
        return tr("The deadline has passed. Edit the goal to set a new one.")
    if required is None:
        return tr("Set a deadline to see how much to save each month.")
    return tr("Save {0} per month to finish on time.", format_money(required))
