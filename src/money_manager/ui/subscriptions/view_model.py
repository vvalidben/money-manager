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
from money_manager.core.i18n import tr

FREQUENCY_TEXT = {
    Frequency.WEEKLY: tr("Weekly"),
    Frequency.MONTHLY: tr("Monthly"),
    Frequency.QUARTERLY: tr("Every 3 months"),
    Frequency.YEARLY: tr("Yearly"),
}
PERIOD_TEXT = {
    Frequency.WEEKLY: "week",
    Frequency.MONTHLY: "month",
    Frequency.QUARTERLY: "quarter",
    Frequency.YEARLY: "year",
}
TABLE_HEADERS = (tr("Name"), tr("Category"), tr("Amount"), tr("Frequency"), tr("Per month"), tr("Next payment"), tr("Status"))


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
        tr("Active") if subscription.is_active else tr("Paused"),
    )


def upcoming_row(payment: UpcomingPayment) -> UpcomingRowView:
    days = payment.days_until
    if days < 0:
        when = tr("Overdue by {0} {1}", -days, tr("day") if days == -1 else tr("days"))
    elif days == 0:
        when = tr("Due today")
    elif days == 1:
        when = tr("Tomorrow")
    else:
        when = tr("In {0} days", days)
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
        StatView(tr("Monthly cost"), format_money(stats.monthly_total),
                 tr("{0} per year", format_money(stats.yearly_total))),
        StatView(tr("Active subscriptions"), str(len(stats.active)),
                 f"{stats.inactive_count} paused"),
        StatView(
            tr("Due in the next {0} days", stats.horizon_days),
            format_money(stats.upcoming_total),
            f"{len(upcoming)} {'payment' if len(upcoming) == 1 else 'payments'}"
            + (tr(" · {0} overdue", overdue) if overdue else ""),
            "outflow" if overdue else "neutral",
        ),
        StatView(
            tr("Most expensive"),
            top.name if top else "—",
            tr("{0} per month", format_money(top.monthly_cost)) if top else tr("No active subscriptions"),
        ),
    )


def category_cost_rows(stats: SubscriptionStats) -> list[CategorySpending]:
    """Monthly cost per category, shaped for the shared category bar chart."""
    return [
        CategorySpending(int(row.key), row.name, row.monthly_cost, row.share)
        for row in stats.by_category
    ]
