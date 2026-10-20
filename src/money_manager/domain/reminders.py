"""Reminders: what deserves a notification today (pure).

* a subscription payment due tomorrow, today or overdue;
* a budget near its limit or over it (once per level and month);
* a loan to repay — or to be repaid — within three days, or overdue;
* the forecast balance going below zero within 30 days (once a month).

Each reminder has a stable ``key``; the caller remembers the keys already
shown so the same reminder never appears twice.
"""

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from money_manager.core.i18n import tr
from money_manager.domain.budgets import BudgetLevel, BudgetStatus
from money_manager.domain.debts import Debt, DebtDirection
from money_manager.domain.forecast import Forecast
from money_manager.domain.money import Money
from money_manager.domain.subscriptions import UpcomingPayment

PAYMENT_DAYS_AHEAD = 1
LOAN_DAYS_AHEAD = 3
FORECAST_DAYS_AHEAD = 30


@dataclass(frozen=True, slots=True)
class Reminder:
    key: str
    title: str
    body: str
    page: str  # the page that shows the details


def collect_reminders(today: date, *, payments: Iterable[UpcomingPayment],
                      budgets: Iterable[BudgetStatus], debts: Iterable[Debt],
                      forecast: Forecast | None,
                      money: Callable[[Money], str],
                      day_text: Callable[[date], str]) -> list[Reminder]:
    """``money`` and ``day_text`` format amounts and dates for display."""
    reminders: list[Reminder] = []
    for payment in payments:
        if payment.days_until > PAYMENT_DAYS_AHEAD:
            continue
        when = (tr("overdue since {0}", day_text(payment.due_date)) if payment.is_overdue
                else tr("due today") if payment.days_until == 0 else tr("due tomorrow"))
        reminders.append(Reminder(
            f"payment:{payment.subscription.id}:{payment.due_date.isoformat()}",
            tr("Payment {0}", when),
            f"{payment.subscription.name} · {money(payment.amount)}", "subscriptions"))
    month = today.strftime("%Y-%m")
    for status in budgets:
        if status.level is BudgetLevel.ON_TRACK:
            continue
        over = status.level is BudgetLevel.OVER
        reminders.append(Reminder(
            f"budget:{status.budget.category_id}:{month}:{status.level.value}",
            tr("Budget over the limit") if over else tr("Budget near its limit"),
            tr("{0}: {1} spent of {2}", status.category_name, money(status.spent),
               money(status.budget.limit)), "budgets"))
    for debt in debts:
        if debt.is_settled or debt.due_date is None:
            continue
        if debt.due_date > today + timedelta(days=LOAN_DAYS_AHEAD):
            continue
        lent = debt.direction is DebtDirection.LENT
        title = tr("A loan should be repaid to you") if lent else tr("A loan repayment is due")
        reminders.append(Reminder(
            f"loan:{debt.id}:{debt.due_date.isoformat()}", title,
            tr("{0} · {1} left · by {2}", debt.name, money(debt.remaining),
               day_text(debt.due_date)), "accounts"))
    if forecast is not None:
        low = forecast.first_below_zero
        if low is not None and low.day <= today + timedelta(days=FORECAST_DAYS_AHEAD):
            reminders.append(Reminder(
                f"forecast:{month}", tr("Money may get tight"),
                tr("Your balance is projected at {0} on {1}.", money(low.balance),
                   day_text(low.day)), "dashboard"))
    return reminders


def unseen(reminders: Sequence[Reminder], shown: Iterable[str]) -> list[Reminder]:
    seen = set(shown)
    return [r for r in reminders if r.key not in seen]
