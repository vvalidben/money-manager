"""Recurring entries in the UI: the list, the form, and recording on start."""

from collections.abc import Iterator
from datetime import date

import pytest
from PySide6.QtCore import QDate
from PySide6.QtWidgets import QApplication, QDialog

from money_manager.core.config import AppConfig
from money_manager.domain.entities import Account, Category
from money_manager.domain.enums import CategoryKind
from money_manager.services import AppServices
from money_manager.ui import dialogs
from money_manager.ui.main_window import MainWindow
from money_manager.ui.pages import PAGES, TRANSACTIONS_PAGE_KEY
from money_manager.ui.recurring.entry_dialog import RecurringEntryDialog
from money_manager.ui.recurring.recurring_dialog import RecurringDialog
from money_manager.ui.transactions.transactions_page import TransactionsPage
from tests.ui.support import wait_until

SPEC = next(spec for spec in PAGES if spec.key == TRANSACTIONS_PAGE_KEY)  # today: 15 Jun 2026


@pytest.fixture
def setup(app_services: AppServices) -> tuple[Account, Category, Category]:
    bank = app_services.accounts.create("Bank", opening_balance="500",
                                        opening_date=date(2026, 1, 1))
    salary = app_services.categories.create("Salary", CategoryKind.INCOME)
    rent = app_services.categories.create("Rent", CategoryKind.EXPENSE)
    return bank, salary, rent


@pytest.fixture
def dialog(qapp: QApplication, app_services: AppServices,
           setup: object) -> Iterator[RecurringDialog]:
    widget = RecurringDialog(app_services)
    widget.show()
    yield widget
    widget.close()
    widget.deleteLater()


def _fill(form: RecurringEntryDialog, *, kind: str, text: str, amount: str, first: date) -> None:
    form.type_combo.setCurrentIndex(form.type_combo.findData(kind))
    form.description_edit.setText(text)
    form.amount_edit.setText(amount)
    form.date_edit.setDate(QDate(first.year, first.month, first.day))


def test_add_records_past_dates_at_once(dialog: RecurringDialog, app_services: AppServices,
                                        monkeypatch: pytest.MonkeyPatch) -> None:
    assert dialog.empty_label.isVisibleTo(dialog) and not dialog.edit_button.isEnabled()

    def auto(form: RecurringEntryDialog) -> int:
        _fill(form, kind="income", text="Salary", amount="9000", first=date(2026, 5, 1))
        assert [form.category_combo.itemText(i) for i in range(form.category_combo.count())] \
            == ["Salary"]  # income categories only
        return QDialog.DialogCode.Accepted if form.submit() else QDialog.DialogCode.Rejected

    monkeypatch.setattr(RecurringEntryDialog, "exec", auto)
    dialog.add_button.click()

    assert dialog.changed
    assert [dialog.table.item(0, c).text() for c in range(6)] == [
        "Salary", "+9,000.00 MAD", "Monthly, day 1", "01 Jul 2026", "Bank", "Active"]
    assert dialog.status_label.text() == "Recorded now: 2 recorded."
    assert len(app_services.transactions.list()) == 2  # 1 May and 1 June


def test_form_errors_stay_inline(qapp: QApplication, app_services: AppServices,
                                 setup: object) -> None:
    form = RecurringEntryDialog(app_services)
    _fill(form, kind="expense", text="", amount="10", first=date(2026, 6, 20))
    assert not form.submit()
    assert form.fields["description"].error_label.isVisibleTo(form)
    form.deleteLater()


def test_pause_resume_and_delete(dialog: RecurringDialog, app_services: AppServices,
                                 setup: tuple[Account, Category, Category],
                                 monkeypatch: pytest.MonkeyPatch) -> None:
    bank, _salary, rent = setup
    app_services.recurring.create("Rent", type="expense", amount="3000", account_id=bank.id,
                                  category_id=rent.id, frequency="monthly",
                                  first_date=date(2026, 7, 5))
    dialog.load()
    dialog.table.selectRow(0)
    assert dialog.pause_button.text() == "Pause"
    dialog.pause_button.click()
    assert dialog.table.item(0, 5).text() == "Paused"
    dialog.table.selectRow(0)
    assert dialog.pause_button.text() == "Resume"
    dialog.pause_button.click()
    assert dialog.table.item(0, 5).text() == "Active"

    monkeypatch.setattr(dialogs, "confirm_destructive", lambda *_a, **_k: True)
    dialog.table.selectRow(0)
    dialog.delete_button.click()
    assert app_services.recurring.list() == [] and dialog.empty_label.isVisibleTo(dialog)


def test_transactions_page_reloads_after_changes(qapp: QApplication, app_services: AppServices,
                                                 setup: tuple[Account, Category, Category],
                                                 monkeypatch: pytest.MonkeyPatch) -> None:
    bank, salary, _rent = setup
    page = TransactionsPage(SPEC, app_services)
    page.show()
    page.on_shown()
    try:
        def fake() -> RecurringDialog:
            dialog = RecurringDialog(app_services, parent=page)
            app_services.recurring.create("Salary", type="income", amount="100",
                                          account_id=bank.id, category_id=salary.id,
                                          frequency="weekly", first_date=date(2026, 6, 15))
            app_services.recurring.record_due()
            dialog.changed = True
            monkeypatch.setattr(dialog, "exec", lambda: 0)
            return dialog

        monkeypatch.setattr(page, "make_recurring_dialog", fake)
        page.recurring_button.click()
        assert page.model.rowCount() == 1
    finally:
        page.close()


def test_window_records_due_entries_on_start(qapp: QApplication, app_config: AppConfig,
                                             app_services: AppServices,
                                             setup: tuple[Account, Category, Category]) -> None:
    bank, salary, _rent = setup
    app_services.recurring.create("Salary", type="income", amount="9000", account_id=bank.id,
                                  category_id=salary.id, frequency="monthly",
                                  first_date=date(2026, 6, 1))
    window = MainWindow(app_config, app_services)
    window.show()
    try:
        wait_until(lambda: len(app_services.transactions.list()) == 1)
        wait_until(lambda: window.toast.isVisible())
        assert window.recurring_timer.isActive()
        assert window.record_recurring().recorded == 0  # nothing twice
    finally:
        window.close()
