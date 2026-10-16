from collections.abc import Callable, Iterator
from datetime import date

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog

from money_manager.domain.entities import Account, Category, Transaction, TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionSort, TransactionType
from money_manager.domain.money import Money
from money_manager.domain.periods import DatePreset
from money_manager.services import AppServices
from money_manager.ui import dialogs
from money_manager.ui.accounts.account_dialog import AccountDialog
from money_manager.ui.pages import PAGES, TRANSACTIONS_PAGE_KEY
from money_manager.ui.transactions.table_model import Column
from money_manager.ui.transactions.transaction_dialog import TransactionDialog
from money_manager.ui.transactions.transactions_page import PAGE_SIZE, TransactionsPage
from tests.services.support import OPENING_DATE, TODAY

SPEC = next(spec for spec in PAGES if spec.key == TRANSACTIONS_PAGE_KEY)


@pytest.fixture
def page(qapp: QApplication, app_services: AppServices) -> Iterator[TransactionsPage]:
    widget = TransactionsPage(SPEC, app_services)
    widget.resize(1200, 800)
    widget.show()
    widget.on_shown()
    yield widget
    widget.close()
    widget.deleteLater()


@pytest.fixture
def account(app_services: AppServices) -> Account:
    return app_services.accounts.create("Bank", opening_balance="10000", opening_date=OPENING_DATE)


@pytest.fixture
def food(app_services: AppServices) -> Category:
    return app_services.categories.create("Food", CategoryKind.EXPENSE)


@pytest.fixture
def salary(app_services: AppServices) -> Category:
    return app_services.categories.create("Salary", CategoryKind.INCOME)


@pytest.fixture
def record(app_services: AppServices, account: Account) -> Callable[..., Transaction]:
    def _record(type_: TransactionType, amount: str, category: Category | None,
                on: date = TODAY, description: str = "") -> Transaction:
        return app_services.transactions.create(TransactionDraft(
            account.id, type_, amount, on, None if category is None else category.id,
            description=description))
    return _record


def _patch_dialog(monkeypatch: pytest.MonkeyPatch, fill: Callable[[TransactionDialog], None]) -> None:
    """Replace the modal ``exec()`` with: fill the inputs, submit, report the result."""

    def auto_submit(dialog: TransactionDialog) -> int:
        fill(dialog)
        return QDialog.DialogCode.Accepted if dialog.submit() else QDialog.DialogCode.Rejected

    monkeypatch.setattr(TransactionDialog, "exec", auto_submit)


def _visible_descriptions(page: TransactionsPage) -> list[str]:
    return [page.model.row_at(r).description for r in range(page.model.rowCount())]


def _select_row(page: TransactionsPage, row: int) -> None:
    page.table.selectRow(row)


class TestEmptyStates:
    def test_no_account(self, page: TransactionsPage) -> None:
        assert page.showing_empty_state
        assert page.empty_state.heading_label.text() == "Create an account to get started"
        assert not page.add_button.isEnabled()

    def test_create_account_from_empty_state(
        self, page: TransactionsPage, app_services: AppServices, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def fill_and_submit(dialog: AccountDialog) -> int:
            dialog.name_edit.setText("Wallet")
            dialog.balance_edit.setText("1 500,25")
            return QDialog.DialogCode.Accepted if dialog.submit() else QDialog.DialogCode.Rejected

        monkeypatch.setattr(AccountDialog, "exec", fill_and_submit)
        page.empty_state.action_button.click()

        assert [a.name for a in app_services.accounts.list()] == ["Wallet"]
        assert page.balance_card.value == "1,500.25 MAD"
        assert page.empty_state.heading_label.text() == "No transactions yet"
        assert page.add_button.isEnabled()

    def test_no_matches(self, page: TransactionsPage, record, food: Category) -> None:
        record(TransactionType.EXPENSE, "10", food, description="Coffee")
        page.reload()

        page.filter_bar.search_edit.setText("nothing like this")
        page.filter_bar.changed.emit()  # skip the debounce timer

        assert page.showing_empty_state
        assert page.empty_state.heading_label.text() == "No matching transactions"
        page.empty_state.action_button.click()  # "Clear filters"
        assert not page.showing_empty_state
        assert page.filter_bar.search_edit.text() == ""


class TestCrud:
    def test_add_updates_table_and_balance(
        self, page: TransactionsPage, account: Account, salary: Category,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        page.reload()

        def fill(dialog: TransactionDialog) -> None:
            dialog.type_combo.setCurrentIndex(dialog.type_combo.findData(TransactionType.INCOME))
            dialog.amount_edit.setText("12000")
            dialog.description_edit.setText("Salary")

        _patch_dialog(monkeypatch, fill)
        page.add_button.click()

        assert _visible_descriptions(page) == ["Salary"]
        assert page.balance_card.value == "22,000.00 MAD"
        assert page.income_card.value == "+12,000.00 MAD"
        assert page.selected_transaction() is not None  # the new row is selected

    def test_failed_add_changes_nothing(
        self, page: TransactionsPage, account: Account, food: Category,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        page.reload()
        _patch_dialog(monkeypatch, lambda d: d.amount_edit.setText("0"))

        page.add_button.click()

        assert page.showing_empty_state
        assert page.balance_card.value == "10,000.00 MAD"

    def test_edit_recalculates_balance(
        self, page: TransactionsPage, record, food: Category, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        record(TransactionType.EXPENSE, "300", food, description="Lunch")
        page.reload()
        assert page.balance_card.value == "9,700.00 MAD"

        _patch_dialog(monkeypatch, lambda d: d.amount_edit.setText("120.40"))
        _select_row(page, 0)
        page.edit_button.click()

        assert page.balance_card.value == "9,879.60 MAD"
        assert page.model.row_at(0).amount == "−120.40 MAD"

    def test_double_click_edits(
        self, page: TransactionsPage, record, food: Category, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        record(TransactionType.EXPENSE, "300", food)
        page.reload()
        opened: list[Transaction | None] = []
        monkeypatch.setattr(TransactionDialog, "exec", lambda d: opened.append(d._original) or 0)

        _select_row(page, 0)
        page.table.doubleClicked.emit(page.model.index(0, 0))

        assert opened and opened[0] is not None

    def test_delete_after_confirmation(
        self, page: TransactionsPage, app_services: AppServices, record, food: Category,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        record(TransactionType.EXPENSE, "300", food, description="Keep")
        record(TransactionType.EXPENSE, "50", food, description="Remove")
        page.reload()
        asked: list[str] = []
        monkeypatch.setattr(
            dialogs, "confirm_destructive",
            lambda _parent, _title, message, *_a: asked.append(message) or True,
        )

        _select_row(page, _visible_descriptions(page).index("Remove"))
        page.delete_button.click()

        assert "Remove" in asked[0] and "cannot be undone" in asked[0]
        assert _visible_descriptions(page) == ["Keep"]
        assert page.balance_card.value == "9,700.00 MAD"
        assert app_services.balances.total_balance() == Money.of("9700")

    def test_cancelled_delete_keeps_transaction(
        self, page: TransactionsPage, record, food: Category, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        record(TransactionType.EXPENSE, "300", food)
        page.reload()
        monkeypatch.setattr(dialogs, "confirm_destructive", lambda *_a: False)

        _select_row(page, 0)
        page.delete_button.click()

        assert page.model.rowCount() == 1

    def test_rejected_delete_shows_warning(
        self, page: TransactionsPage, app_services: AppServices, account: Account,
        salary: Category, food: Category, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        savings = app_services.allocations.create("Savings")
        app_services.transactions.create(TransactionDraft(
            account.id, TransactionType.INCOME, "100", TODAY, salary.id, description="Bonus",
            allocation_id=savings.id))
        app_services.transactions.create(TransactionDraft(
            account.id, TransactionType.EXPENSE, "80", TODAY, food.id, allocation_id=savings.id))
        page.reload()
        warnings: list[str] = []
        monkeypatch.setattr(dialogs, "confirm_destructive", lambda *_a: True)
        monkeypatch.setattr(dialogs, "show_warning", lambda _p, _t, msg: warnings.append(msg))

        _select_row(page, _visible_descriptions(page).index("Bonus"))
        page.delete_button.click()

        assert warnings and "Savings" in warnings[0]
        assert page.model.rowCount() == 2

    def test_actions_need_a_selection(self, page: TransactionsPage, record, food: Category) -> None:
        record(TransactionType.EXPENSE, "1", food)
        page.reload()
        assert not page.edit_button.isEnabled() and not page.delete_button.isEnabled()

        _select_row(page, 0)

        assert page.edit_button.isEnabled() and page.delete_button.isEnabled()


class TestFiltersSortingPaging:
    @pytest.fixture(autouse=True)
    def _data(self, record, food: Category, salary: Category) -> None:
        record(TransactionType.INCOME, "12000", salary, on=date(2026, 5, 1), description="Salary")
        record(TransactionType.EXPENSE, "4500", food, on=date(2026, 5, 2), description="Big dinner")
        record(TransactionType.EXPENSE, "20", food, on=TODAY, description="Coffee")
        record(TransactionType.ADJUSTMENT_IN, "1", None, on=TODAY, description="Fix")

    def test_type_filter(self, page: TransactionsPage) -> None:
        page.reload()
        page.filter_bar.type_combo.setCurrentIndex(2)  # Expenses

        assert _visible_descriptions(page) == ["Coffee", "Big dinner"]
        assert page.expenses_card.value == "−4,520.00 MAD"
        assert page.income_card.value == "0.00 MAD"

    def test_category_filter(self, page: TransactionsPage, salary: Category) -> None:
        page.reload()
        combo = page.filter_bar.category_combo
        combo.setCurrentIndex(combo.findData(salary.id))

        assert _visible_descriptions(page) == ["Salary"]

    def test_period_filter(self, page: TransactionsPage) -> None:
        page.reload()
        combo = page.filter_bar.period_combo
        combo.setCurrentIndex(combo.findData(DatePreset.THIS_MONTH))  # June 2026

        assert _visible_descriptions(page) == ["Fix", "Coffee"]
        assert page.income_card.label.text().startswith("Income · 01 Jun 2026")

    def test_custom_range(self, page: TransactionsPage) -> None:
        page.reload()
        bar = page.filter_bar
        bar.period_combo.setCurrentIndex(bar.period_combo.findData(DatePreset.CUSTOM))
        assert not bar.start_edit.isHidden()
        bar.start_edit.setDate(bar.start_edit.date().fromString("2026-05-02", "yyyy-MM-dd"))
        bar.end_edit.setDate(bar.end_edit.date().fromString("2026-05-31", "yyyy-MM-dd"))

        assert _visible_descriptions(page) == ["Big dinner"]

    def test_custom_end_cannot_precede_start(self, page: TransactionsPage) -> None:
        bar = page.filter_bar
        bar.period_combo.setCurrentIndex(bar.period_combo.findData(DatePreset.CUSTOM))
        bar.end_edit.setDate(bar.end_edit.date().fromString("2026-01-01", "yyyy-MM-dd"))
        bar.start_edit.setDate(bar.start_edit.date().fromString("2026-06-10", "yyyy-MM-dd"))

        filters = bar.filters()
        assert filters.start is not None and filters.end is not None
        assert filters.start <= filters.end

    def test_search(self, page: TransactionsPage) -> None:
        page.reload()
        page.filter_bar.search_edit.setText("dinner")
        page.filter_bar.changed.emit()

        assert _visible_descriptions(page) == ["Big dinner"]

    def test_header_click_sorts_through_service(self, page: TransactionsPage) -> None:
        page.reload()
        page.table.sortByColumn(Column.AMOUNT, Qt.SortOrder.AscendingOrder)

        assert page.query.sort is TransactionSort.AMOUNT and not page.query.descending
        assert _visible_descriptions(page) == ["Big dinner", "Coffee", "Fix", "Salary"]

    def test_paging(
        self, page: TransactionsPage, record, food: Category
    ) -> None:
        for index in range(PAGE_SIZE):
            record(TransactionType.EXPENSE, "1", food, on=date(2026, 4, 1), description=f"#{index}")
        page.reload()

        assert page.model.rowCount() == PAGE_SIZE
        assert page.result_label.text() == f"Showing 1–{PAGE_SIZE} of {PAGE_SIZE + 4}"
        assert not page.previous_button.isEnabled() and page.next_button.isEnabled()

        page.next_button.click()

        assert page.model.rowCount() == 4
        assert page.result_label.text() == f"Showing {PAGE_SIZE + 1}–{PAGE_SIZE + 4} of {PAGE_SIZE + 4}"
        assert page.previous_button.isEnabled() and not page.next_button.isEnabled()

    def test_filter_change_returns_to_first_page(
        self, page: TransactionsPage, record, food: Category
    ) -> None:
        for _ in range(PAGE_SIZE):
            record(TransactionType.EXPENSE, "1", food, on=date(2026, 4, 1))
        page.reload()
        page.next_button.click()

        page.filter_bar.type_combo.setCurrentIndex(2)

        assert page.query.offset == 0
