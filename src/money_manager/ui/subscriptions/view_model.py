"""Display text for subscriptions (pure presentation, no Qt, no calculations)."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

from money_manager.domain.dashboard import CategorySpending
from money_manager.domain.subscriptions import (
    Frequency,
    Subscription,
    SubscriptionStats,
    UpcomingPayment,
)
from money_manager.ui.dashboard.view_model import StatView
from money_manager.ui.formatting import format_date, format_money

FREQUENCY_TEXT = {
    Frequency.WEEKLY: "Weekly",
    Frequency.MONTHLY: "Monthly",
    Frequency.QUARTERLY: "Every 3 months",
    Frequency.YEARLY: "Yearly",
}
PERIOD_TEXT = {
    Frequency.WEEKLY: "week",
    Frequency.MONTHLY: "month",
    Frequency.QUARTERLY: "quarter",
    Frequency.YEARLY: "year",
}
TABLE_HEADERS = ("Name", "Category", "Amount", "Frequency", "Per month", "Next payment", "Status")


@dataclass(frozen=True, slots=True)
class UpcomingRowView:
    subscription_id: int
    due_date: date
    name: str
    amount: str
    when: str
    is_overdue: bool
    can_be_confirmed: bool


def subscription_row(
    subscription: Subscription, category_names: Mapping[int, str], today: date
) -> tuple[str, ...]:
    next_date = subscription.next_payment_date
    overdue = subscription.is_active and next_date < today
    return (
        subscription.name,
        category_names.get(subscription.category_id, "?"),
        f"{format_money(subscription.amount)} / {PERIOD_TEXT[subscription.frequency]}",
        FREQUENCY_TEXT[subscription.frequency],
        format_money(subscription.monthly_cost),
        format_date(next_date) + (" (overdue)" if overdue else ""),
        "Active" if subscription.is_active else "Paused",
    )


def upcoming_row(payment: UpcomingPayment) -> UpcomingRowView:
    days = payment.days_until
    if days < 0:
        when = f"Overdue by {-days} {'day' if days == -1 else 'days'}"
    elif days == 0:
        when = "Due today"
    elif days == 1:
        when = "Tomorrow"
    else:
        when = f"In {days} days"
    return UpcomingRowView(
        subscription_id=payment.subscription.id,
        due_date=payment.due_date,
        name=payment.subscription.name,
        amount=format_money(payment.amount),
        when=f"{format_date(payment.due_date)} · {when}",
        is_overdue=payment.is_overdue,
        can_be_confirmed=payment.can_be_confirmed,
    )


def summary_stats(stats: SubscriptionStats) -> tuple[StatView, ...]:
    upcoming = [p for p in stats.upcoming if not p.is_overdue]
    overdue = len(stats.overdue)
    top = stats.most_expensive
    return (
        StatView("Monthly cost", format_money(stats.monthly_total),
                 f"{format_money(stats.yearly_total)} per year"),
        StatView("Active subscriptions", str(len(stats.active)),
                 f"{stats.inactive_count} paused"),
        StatView(
            f"Due in the next {stats.horizon_days} days",
            format_money(stats.upcoming_total),
            f"{len(upcoming)} {'payment' if len(upcoming) == 1 else 'payments'}"
            + (f" · {overdue} overdue" if overdue else ""),
            "outflow" if overdue else "neutral",
        ),
        StatView(
            "Most expensive",
            top.name if top else "—",
            f"{format_money(top.monthly_cost)} per month" if top else "No active subscriptions",
        ),
    )


def category_cost_rows(stats: SubscriptionStats) -> list[CategorySpending]:
    """Monthly cost per category, shaped for the shared category bar chart."""
    return [
        CategorySpending(int(row.key), row.name, row.monthly_cost, row.share)
        for row in stats.by_category
    ]
