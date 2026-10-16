from collections.abc import Iterator
from datetime import date, timedelta

import pytest
from PySide6.QtWidgets import QApplication, QDialog

from money_manager.domain.entities import Account, Category
from money_manager.domain.enums import CategoryKind
from money_manager.domain.money import Money
from money_manager.domain.subscriptions import Frequency, PaymentStatus
from money_manager.services import AppServices
from money_manager.ui import dialogs
from money_manager.ui.pages import PAGES, SUBSCRIPTIONS_PAGE_KEY
from money_manager.ui.subscriptions.payment_dialog import RecordPaymentDialog
from money_manager.ui.subscriptions.subscription_dialog import SubscriptionDialog
from money_manager.ui.subscriptions.subscriptions_page import SKIP, SubscriptionsPage
from money_manager.ui.subscriptions.view_model import (
    subscription_row,
    summary_stats,
    upcoming_row,
)
from money_manager.ui.transactions.filter_bar import to_qdate
from tests.services.support import OPENING_DATE, TODAY

SPEC = next(spec for spec in PAGES if spec.key == SUBSCRIPTIONS_PAGE_KEY)


@pytest.fixture
def bank(app_services: AppServices) -> Account:
    return app_services.accounts.create("Bank", opening_balance="5000", opening_date=OPENING_DATE)


@pytest.fixture
def streaming(app_services: AppServices) -> Category:
    return app_services.categories.create("Subscriptions", CategoryKind.EXPENSE)


@pytest.fixture
def examples(app_services: AppServices, streaming: Category, bank: Account) -> None:
    for name, amount, due in (("Netflix", "150", TODAY + timedelta(days=5)),
                              ("Spotify", "70", TODAY - timedelta(days=3)),
                              ("Internet", "300", TODAY + timedelta(days=12))):
        app_services.subscriptions.create(name, amount=amount, frequency="monthly",
                                          next_payment_date=due, category_id=streaming.id,
                                          account_id=bank.id)


@pytest.fixture
def page(qapp: QApplication, app_services: AppServices) -> Iterator[SubscriptionsPage]:
    widget = SubscriptionsPage(SPEC, app_services)
    widget.resize(1200, 900)
    widget.show()
    widget.on_shown()
    yield widget
    widget.close()
    widget.deleteLater()


class TestViewModel:
    def test_rows_and_summary(self, app_services: AppServices, examples: None,
                              streaming: Category) -> None:
        stats = app_services.subscriptions.statistics()
        names = {streaming.id: "Subscriptions"}

        rows = {s.name: subscription_row(s, names, TODAY) for s in stats.subscriptions}
        assert rows["Netflix"] == ("Netflix", "Subscriptions", "150.00 MAD / month", "Monthly",
                                   "150.00 MAD", "20 Jun 2026", "Active")
        assert rows["Spotify"][5] == "12 Jun 2026 (overdue)"

        cards = summary_stats(stats)
        assert (cards[0].value, cards[0].caption) == ("520.00 MAD", "6,240.00 MAD per year")
        assert cards[2].caption == "3 payments · 1 overdue"
        assert (cards[3].value, cards[3].caption) == ("Internet", "300.00 MAD per month")

        upcoming = [upcoming_row(p) for p in stats.upcoming]
        assert upcoming[0].when == "12 Jun 2026 · Overdue by 3 days" and upcoming[0].is_overdue
        assert upcoming[1].when == "20 Jun 2026 · In 5 days"


class TestSubscriptionDialog:
    def test_create(self, qapp: QApplication, app_services: AppServices, streaming: Category,
                    bank: Account) -> None:
        dialog = SubscriptionDialog(app_services)
        dialog.name_edit.setText("Domain name")
        dialog.amount_edit.setText("1 200")
        dialog.frequency_combo.setCurrentIndex(dialog.frequency_combo.findData("yearly"))
        dialog.date_edit.setDate(to_qdate(date(2026, 9, 30)))
        dialog.account_combo.setCurrentIndex(dialog.account_combo.findData(bank.id))

        assert dialog.submit()

        saved = dialog.saved
        assert saved is not None and saved.frequency is Frequency.YEARLY
        assert saved.monthly_cost == Money.of("100") and saved.account_id == bank.id
        assert saved.category_id == streaming.id

    def test_errors_inline(self, qapp: QApplication, app_services: AppServices,
                           streaming: Category) -> None:
        dialog = SubscriptionDialog(app_services)
        dialog.name_edit.setText("Netflix")
        dialog.amount_edit.setText("0")

        assert not dialog.submit()
        assert dialog.fields["amount"].error == "Amount must be greater than zero."
        assert app_services.subscriptions.list() == []

    def test_needs_a_category(self, qapp: QApplication, app_services: AppServices) -> None:
        dialog = SubscriptionDialog(app_services)
        dialog.name_edit.setText("Netflix")
        dialog.amount_edit.setText("150")

        assert not dialog.submit()
        assert "Choose a category" in dialog.fields["category_id"].error

    def test_new_category_inline(self, qapp: QApplication, app_services: AppServices) -> None:
        dialog = SubscriptionDialog(app_services)
        dialog.create_category("Streaming")
        assert dialog.category_combo.currentText() == "Streaming"

    def test_edit(self, qapp: QApplication, app_services: AppServices, examples: None) -> None:
        netflix = next(s for s in app_services.subscriptions.list() if s.name == "Netflix")
        dialog = SubscriptionDialog(app_services, subscription=netflix)

        assert dialog.amount_edit.text() == "150.00" and dialog.frequency is Frequency.MONTHLY
        dialog.amount_edit.setText("190")
        assert dialog.submit()
        assert app_services.subscriptions.get(netflix.id).amount == Money.of("190")


class TestRecordPaymentDialog:
    def test_records_one_expense(self, qapp: QApplication, app_services: AppServices,
                                 examples: None, bank: Account) -> None:
        spotify = next(s for s in app_services.subscriptions.list() if s.name == "Spotify")
        dialog = RecordPaymentDialog(app_services, spotify, spotify.next_payment_date)

        assert dialog.date_edit.date().toPython() == spotify.next_payment_date
        assert dialog.account_combo.currentData() == bank.id
        dialog.amount_edit.setText("75")
        assert dialog.submit()

        assert dialog.saved is not None and dialog.saved.amount == Money.of("75")
        assert app_services.balances.balance(bank.id) == Money.of("4925")

    def test_second_attempt_is_refused(self, qapp: QApplication, app_services: AppServices,
                                       examples: None) -> None:
        spotify = next(s for s in app_services.subscriptions.list() if s.name == "Spotify")
        first = RecordPaymentDialog(app_services, spotify, spotify.next_payment_date)
        stale = RecordPaymentDialog(app_services, spotify, spotify.next_payment_date)

        assert first.submit()
        assert not stale.submit()  # e.g. a second window left open
        assert "already been confirmed" in stale.form_error.text()
        assert len(app_services.transactions.list()) == 1


class TestPage:
    def test_empty_state(self, page: SubscriptionsPage) -> None:
        assert not page.empty_state.isHidden()
        assert page.list_card.isHidden()

    def test_populated(self, page: SubscriptionsPage, examples: None) -> None:
        page.refresh()

        assert page.table.rowCount() == 3
        assert page.stat_cards[0].value == "520.00 MAD"
        # Spotify's overdue payment, then everything due within 30 days (Spotify again on 12 Jul).
        assert [r.name for r in page.upcoming_card.rows] == [
            "Spotify", "Netflix", "Internet", "Spotify"
        ]
        assert page.cost_card.chart.hover_texts == ["Subscriptions\n520.00 MAD · 100.0%"]

    def test_record_from_upcoming(self, page: SubscriptionsPage, app_services: AppServices,
                                  examples: None, monkeypatch: pytest.MonkeyPatch) -> None:
        page.refresh()
        monkeypatch.setattr(
            RecordPaymentDialog, "exec",
            lambda d: QDialog.DialogCode.Accepted if d.submit() else QDialog.DialogCode.Rejected,
        )

        page.upcoming_card.record_buttons[0].click()  # Spotify, overdue

        spotify = next(s for s in app_services.subscriptions.list() if s.name == "Spotify")
        assert spotify.next_payment_date == TODAY - timedelta(days=3) + timedelta(days=30)
        assert page.stat_cards[2].caption_label.text() == "3 payments"  # no longer overdue

    def test_skip_from_upcoming(self, page: SubscriptionsPage, app_services: AppServices,
                                examples: None, monkeypatch: pytest.MonkeyPatch) -> None:
        page.refresh()
        monkeypatch.setattr(dialogs, "choose", lambda *_args: SKIP)

        page.upcoming_card.skip_buttons[0].click()

        spotify = next(s for s in app_services.subscriptions.list() if s.name == "Spotify")
        [payment] = app_services.subscriptions.payments(spotify.id)
        assert payment.status is PaymentStatus.SKIPPED
        assert app_services.transactions.list() == []

    def test_later_dates_wait_for_earlier_ones(
        self, page: SubscriptionsPage, app_services: AppServices, streaming: Category
    ) -> None:
        app_services.subscriptions.create("Weekly box", amount="50", frequency="weekly",
                                          next_payment_date=TODAY, category_id=streaming.id)
        page.refresh()

        buttons = page.upcoming_card.record_buttons
        assert buttons[0].isEnabled() and not buttons[1].isEnabled()

    def test_pause_resume_and_delete(self, page: SubscriptionsPage, app_services: AppServices,
                                     examples: None, monkeypatch: pytest.MonkeyPatch) -> None:
        page.refresh()
        page.table.selectRow(0)
        name = page.selected().name  # type: ignore[union-attr]

        page.pause_button.click()
        assert not next(s for s in app_services.subscriptions.list() if s.name == name).is_active
        assert page.pause_button.text() == "Resume"
        page.pause_button.click()
        assert next(s for s in app_services.subscriptions.list() if s.name == name).is_active

        monkeypatch.setattr(dialogs, "confirm_destructive", lambda *_args: True)
        page.table.selectRow(0)
        page.delete_button.click()
        assert name not in [s.name for s in app_services.subscriptions.list()]
        assert page.table.rowCount() == 2
