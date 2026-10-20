"""The cash-flow forecast: gathers today's balance, the scheduled items and the
usual income and spending, then lets ``domain.forecast`` project them."""

from collections.abc import Callable
from datetime import date, timedelta

from money_manager.core.i18n import tr
from money_manager.domain.debts import DebtDirection
from money_manager.domain.enums import TransactionType
from money_manager.domain.forecast import (
    FORECAST_MONTHS,
    HISTORY_MONTHS,
    EventKind,
    Forecast,
    ForecastEvent,
    build_forecast,
    monthly_equivalent,
    usual_flow,
)
from money_manager.domain.money import Money
from money_manager.domain.periods import DateRange, add_months, month_start, shift_months
from money_manager.domain.subscriptions import occurrences
from money_manager.services.account_service import AccountService
from money_manager.services.balance_service import BalanceService
from money_manager.services.debt_service import DebtService
from money_manager.services.recurring_service import RecurringService
from money_manager.services.statistics_service import StatisticsService
from money_manager.services.subscription_service import SubscriptionService


class ForecastService:
    def __init__(self, *, accounts: AccountService, balances: BalanceService,
                 recurring: RecurringService, subscriptions: SubscriptionService,
                 debts: DebtService, statistics: StatisticsService,
                 today: Callable[[], date] = date.today, base_currency: str) -> None:
        self._accounts = accounts
        self._balances = balances
        self._recurring = recurring
        self._subscriptions = subscriptions
        self._debts = debts
        self._statistics = statistics
        self._today = today
        self._currency = base_currency

    def forecast(self, months: int = FORECAST_MONTHS) -> Forecast | None:
        """None until an account exists."""
        accounts = self._accounts.list()
        if not accounts:
            return None
        today = self._today()
        end = shift_months(today, months) - timedelta(days=1)
        events: list[ForecastEvent] = []
        scheduled_in: list[Money] = []
        scheduled_out: list[Money] = []

        for entry in self._recurring.list():
            if not entry.is_active:
                continue
            income = entry.type is TransactionType.INCOME
            for day in occurrences(entry.next_date, entry.frequency, entry.anchor_day, end):
                events.append(ForecastEvent(day, entry.description,
                                            entry.amount if income else -entry.amount,
                                            EventKind.RECURRING))
            monthly = monthly_equivalent(entry.amount, entry.frequency.payments_per_year)
            (scheduled_in if income else scheduled_out).append(monthly)

        for subscription in self._subscriptions.list():
            if not subscription.is_active:
                continue
            for day in occurrences(subscription.next_payment_date, subscription.frequency,
                                   subscription.anchor_day, end):
                events.append(ForecastEvent(day, subscription.name, -subscription.amount,
                                            EventKind.SUBSCRIPTION))
            scheduled_out.append(subscription.monthly_cost)

        for debt in self._debts.list():
            if debt.is_settled or debt.due_date is None or not today <= debt.due_date <= end:
                continue
            if debt.direction is DebtDirection.LENT:
                events.append(ForecastEvent(debt.due_date, tr("{0} repays", debt.name),
                                            debt.remaining, EventKind.LOAN))
            else:
                events.append(ForecastEvent(debt.due_date, tr("Repay {0}", debt.name),
                                            -debt.remaining, EventKind.LOAN))

        months_used, income, spending = self._history(min(a.opening_date for a in accounts),
                                                      today)
        return build_forecast(
            today, self._balances.total_balance(today), events,
            usual_income=usual_flow(income, months_used, scheduled_in),
            usual_spending=usual_flow(spending, months_used, scheduled_out),
            history_months=months_used, months=months)

    def _history(self, tracking_start: date, today: date) -> tuple[int, Money, Money]:
        """Income and expenses of the last complete months (up to three)."""
        last_complete_end = month_start(today) - timedelta(days=1)
        first = max(add_months(today, -HISTORY_MONTHS), month_start(tracking_start))
        if tracking_start > first:  # the first month was only partly tracked
            first = add_months(first, 1)
        if first > last_complete_end:
            zero = Money.zero(self._currency)
            return 0, zero, zero
        months = ((last_complete_end.year - first.year) * 12
                  + last_complete_end.month - first.month + 1)
        totals = self._statistics.report(DateRange(first, last_complete_end)).totals
        return months, totals.income, totals.expenses
