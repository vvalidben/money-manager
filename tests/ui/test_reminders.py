"""Reminders (what to notify) and the notification-area behaviour (today: 15 Jun 2026)."""

from datetime import date

import pytest
from PySide6.QtWidgets import QApplication

from money_manager.core.config import AppConfig
from money_manager.domain.entities import Account, TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.reminders import Reminder
from money_manager.services import AppServices
from money_manager.ui.formatting import format_date, format_money
from money_manager.ui.main_window import MainWindow


@pytest.fixture
def setup(app_services: AppServices) -> Account:
    bank = app_services.accounts.create("Bank", opening_balance="5000",
                                        opening_date=date(2026, 1, 1))
    food = app_services.categories.create("Food", CategoryKind.EXPENSE)
    app_services.subscriptions.create("Netflix", amount="65", frequency="monthly",
                                      next_payment_date=date(2026, 6, 16), category_id=food.id)
    app_services.subscriptions.create("Gym", amount="300", frequency="monthly",
                                      next_payment_date=date(2026, 6, 25), category_id=food.id)
    app_services.budgets.set(food.id, "100")
    app_services.transactions.create(TransactionDraft(bank.id, TransactionType.EXPENSE, "90",
                                                      date(2026, 6, 2), food.id))
    app_services.debts.create("Sami", direction="lent", amount="200",
                              start_date=date(2026, 6, 1), due_date=date(2026, 6, 17))
    return bank


def due(services: AppServices) -> list[Reminder]:
    return services.reminders.due(format_money, format_date)


def test_what_is_reminded(app_services: AppServices, setup: Account) -> None:
    reminders = {r.key: r for r in due(app_services)}
    assert set(reminders) == {"payment:1:2026-06-16", "budget:1:2026-06:near_limit",
                              "loan:1:2026-06-17"}
    payment = reminders["payment:1:2026-06-16"]
    assert (payment.title, payment.body, payment.page) == (
        "Payment due tomorrow", "Netflix · 65.00 MAD", "subscriptions")
    assert reminders["budget:1:2026-06:near_limit"].body == "Food: 90.00 MAD spent of 100.00 MAD"
    assert reminders["loan:1:2026-06-17"].title == "A loan should be repaid to you"


def test_each_reminder_once(app_services: AppServices, setup: Account) -> None:
    first = due(app_services)
    app_services.reminders.mark_shown(first)
    assert due(app_services) == []
    # A new level is a new reminder.
    bank = setup
    food = app_services.categories.list(CategoryKind.EXPENSE)[0]
    app_services.transactions.create(TransactionDraft(bank.id, TransactionType.EXPENSE, "20",
                                                      date(2026, 6, 3), food.id))
    assert [r.key for r in due(app_services)] == ["budget:1:2026-06:over"]


def test_switched_off(app_services: AppServices, setup: Account) -> None:
    app_services.settings.set_reminders_enabled(False)
    assert due(app_services) == []


def test_low_balance_warning(app_services: AppServices) -> None:
    bank = app_services.accounts.create("Bank", opening_balance="100",
                                        opening_date=date(2026, 6, 1))
    rent = app_services.categories.create("Rent", CategoryKind.EXPENSE)
    app_services.recurring.create("Rent", type="expense", amount="3000", account_id=bank.id,
                                  category_id=rent.id, frequency="monthly",
                                  first_date=date(2026, 7, 1))
    [reminder] = due(app_services)
    assert reminder.key == "forecast:2026-06" and reminder.page == "dashboard"
    assert "01 Jul 2026" in reminder.body


def test_old_keys_are_forgotten(app_services: AppServices) -> None:
    settings = app_services.settings
    settings.mark_reminders_shown(["old"], date(2026, 1, 1))
    settings.mark_reminders_shown(["new"], date(2026, 6, 15))
    assert settings.shown_reminders() == {"new": "2026-06-15"}


class FakeTray:
    available = True

    def __init__(self) -> None:
        self.notified: list[Reminder] = []
        self.messages: list[str] = []
        self.visible = None

    def notify(self, reminder: Reminder) -> None:
        self.notified.append(reminder)

    def message(self, title: str, _body: str) -> None:
        self.messages.append(title)

    def set_visible(self, visible: bool) -> None:
        self.visible = visible


class TestWindow:
    def test_without_a_tray_the_window_shows_a_notice(
            self, qapp: QApplication, app_config: AppConfig, app_services: AppServices,
            setup: Account) -> None:
        window = MainWindow(app_config, app_services)
        window.show()
        try:
            shown = window.check_reminders()
            assert len(shown) == 3 and window.toast.isVisible()
            assert window.check_reminders() == []  # never twice
        finally:
            window.close()

    def test_notifications_and_keep_in_tray(self, qapp: QApplication, app_config: AppConfig,
                                            app_services: AppServices, setup: Account) -> None:
        window = MainWindow(app_config, app_services)
        window.show()
        fake = FakeTray()
        window.tray = fake  # type: ignore[assignment]
        try:
            window.check_reminders()
            assert [r.page for r in fake.notified] == ["subscriptions", "budgets", "accounts"]

            app_services.settings.set_keep_in_tray(True)
            app_services.settings.set_app_lock_enabled(True)
            window.app_lock.configure()
            window.close()
            assert window.isHidden() and window.app_lock.locked  # hidden, and locked
            assert fake.messages == ["Money Manager is still running"]

            window.open_from_tray("budgets")
            assert window.isVisible() and window.current_page.spec.key == "budgets"
            window._quitting = True  # what "Quit" does before quitting the app
        finally:
            window.close()
        assert window.isHidden()

    def test_tray_icon_follows_the_settings(self, qapp: QApplication, app_config: AppConfig,
                                            app_services: AppServices) -> None:
        window = MainWindow(app_config, app_services)
        fake = FakeTray()
        window.tray = fake  # type: ignore[assignment]
        app_services.settings.set_reminders_enabled(False)
        window.update_tray()
        assert fake.visible is False
        app_services.settings.set_keep_in_tray(True)
        window.update_tray()
        assert fake.visible is True
        window.close()


def test_settings_card(qapp: QApplication, app_services: AppServices) -> None:
    from money_manager.ui.settings.notifications_card import NotificationsCard

    card = NotificationsCard(app_services)
    changes: list[bool] = []
    card.changed.connect(lambda: changes.append(True))
    assert card.reminders_box.isChecked() and not card.tray_box.isChecked()
    card.tray_box.setChecked(True)
    card.reminders_box.setChecked(False)
    assert app_services.settings.keep_in_tray() and not app_services.settings.reminders_enabled()
    assert changes == [True, True]
    card.deleteLater()
