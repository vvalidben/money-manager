"""Reminders to show now: collected from the services, minus those already shown."""

from collections.abc import Callable
from datetime import date

from money_manager.core.errors import MoneyManagerError
from money_manager.domain.money import Money
from money_manager.domain.reminders import Reminder, collect_reminders, unseen
from money_manager.services.budget_service import BudgetService
from money_manager.services.debt_service import DebtService
from money_manager.services.forecast_service import ForecastService
from money_manager.services.settings_service import SettingsService
from money_manager.services.subscription_service import SubscriptionService


class ReminderService:
    def __init__(self, *, settings: SettingsService, subscriptions: SubscriptionService,
                 budgets: BudgetService, debts: DebtService, forecast: ForecastService,
                 today: Callable[[], date] = date.today) -> None:
        self._settings = settings
        self._subscriptions = subscriptions
        self._budgets = budgets
        self._debts = debts
        self._forecast = forecast
        self._today = today

    def enabled(self) -> bool:
        return self._settings.reminders_enabled()

    def due(self, money: Callable[[Money], str], day_text: Callable[[date], str]) -> list[Reminder]:
        """Reminders not shown before (empty when reminders are switched off)."""
        if not self.enabled():
            return []
        today = self._today()
        try:
            forecast = self._forecast.forecast(1)
        except MoneyManagerError:
            forecast = None
        reminders = collect_reminders(
            today, payments=self._subscriptions.upcoming(2),
            budgets=self._budgets.overview().statuses, debts=self._debts.list(),
            forecast=forecast, money=money, day_text=day_text)
        return unseen(reminders, self._settings.shown_reminders())

    def mark_shown(self, reminders: list[Reminder]) -> None:
        if reminders:
            self._settings.mark_reminders_shown([r.key for r in reminders], self._today())
