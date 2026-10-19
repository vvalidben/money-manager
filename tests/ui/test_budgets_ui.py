"""Budgets page: empty state, creating, editing and removing a budget."""

from collections.abc import Callable, Iterator
from datetime import date

import pytest
from PySide6.QtWidgets import QApplication, QDialog

from money_manager.domain.entities import Account, Category, TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.money import Money
from money_manager.services import AppServices
from money_manager.ui import dialogs
from money_manager.ui.budgets.budget_dialog import BudgetDialog
from money_manager.ui.budgets.budgets_page import BudgetsPage
from money_manager.ui.pages import BUDGETS_PAGE_KEY, PAGES
from tests.services.support import fixed_today

SPEC = next(spec for spec in PAGES if spec.key == BUDGETS_PAGE_KEY)


@pytest.fixture
def food(app_services: AppServices) -> Category:
    return app_services.categories.create("Groceries", CategoryKind.EXPENSE)


@pytest.fixture
def bank(app_services: AppServices) -> Account:
    return app_services.accounts.create("Bank", opening_balance="5000",
                                        opening_date=date(2025, 1, 1))


@pytest.fixture
def page(qapp: QApplication, app_services: AppServices) -> Iterator[BudgetsPage]:
    widget = BudgetsPage(SPEC, app_services)
    widget.resize(1100, 800)
    widget.show()
    widget.on_shown()
    yield widget
    widget.close()
    widget.deleteLater()


def _auto(monkeypatch: pytest.MonkeyPatch, fill: Callable[[BudgetDialog], None]) -> None:
    def auto_submit(dialog: BudgetDialog) -> int:
        fill(dialog)
        return QDialog.DialogCode.Accepted if dialog.submit() else QDialog.DialogCode.Rejected

    monkeypatch.setattr(BudgetDialog, "exec", auto_submit)


def test_empty_state_offers_one_action(page: BudgetsPage) -> None:
    assert page.empty_state.isVisible() and not page.new_button.isVisible()
    assert not page.stats_row.isVisible()


def test_create_shows_a_card_with_this_months_spending(
        page: BudgetsPage, app_services: AppServices, food: Category, bank: Account,
        monkeypatch: pytest.MonkeyPatch) -> None:
    app_services.transactions.create(TransactionDraft(bank.id, TransactionType.EXPENSE, "1750",
                                                      fixed_today(), food.id))

    def fill(dialog: BudgetDialog) -> None:
        dialog.category_combo.setCurrentIndex(dialog.category_combo.findData(food.id))
        dialog.amount_edit.setText("2000")

    _auto(monkeypatch, fill)
    notices: list[tuple[str, str]] = []
    page.notice.connect(lambda title, detail: notices.append((title, detail)))
    page.empty_state.action_button.click()

    card = page.card_for(food.id)
    assert (card.view.spent, card.view.limit, card.view.status) == (
        "1,750.00 MAD", "of 2,000.00 MAD", "Near limit")
    assert card.bar.property("level") == "near_limit"
    assert card.view.left == "250.00 MAD left this month"
    assert notices == [("Budget saved", "Groceries · 2,000.00 MAD a month")]
    assert [c.value for c in page.stat_cards] == ["2,000.00 MAD", "1,750.00 MAD",
                                                  "250.00 MAD", "0"]


def test_edit_keeps_the_category_and_changes_the_limit(
        page: BudgetsPage, app_services: AppServices, food: Category,
        monkeypatch: pytest.MonkeyPatch) -> None:
    app_services.budgets.set(food.id, "2000")
    page.refresh()
    seen: list[bool] = []

    def fill(dialog: BudgetDialog) -> None:
        seen.append(dialog.category_combo.isEnabled())
        assert dialog.amount_edit.text() == "2000.00"
        dialog.amount_edit.setText("2500")

    _auto(monkeypatch, fill)
    page.edit_budget(food.id)
    assert seen == [False]
    [status] = app_services.budgets.overview().statuses
    assert status.budget.limit == Money.of("2500")


def test_remove_after_confirmation(page: BudgetsPage, app_services: AppServices,
                                   food: Category, monkeypatch: pytest.MonkeyPatch) -> None:
    app_services.budgets.set(food.id, "2000")
    page.refresh()
    monkeypatch.setattr(dialogs, "confirm_destructive", lambda *_args: True)
    page.remove_budget(food.id)
    assert app_services.budgets.overview().statuses == ()
    assert page.empty_state.isVisible()


def test_dialog_explains_missing_category_and_bad_amounts(
        qapp: QApplication, app_services: AppServices) -> None:
    dialog = BudgetDialog(app_services)
    assert not dialog.submit()
    assert "Choose a category" in dialog.fields["category_id"].error
    app_services.categories.create("Dining", CategoryKind.EXPENSE)
    dialog = BudgetDialog(app_services)
    dialog.amount_edit.setText("0")
    assert not dialog.submit()
    assert dialog.fields["amount"].error
    dialog.deleteLater()


def test_categories_with_a_budget_are_not_offered_again(
        qapp: QApplication, app_services: AppServices, food: Category) -> None:
    other = app_services.categories.create("Dining", CategoryKind.EXPENSE)
    app_services.budgets.set(food.id, "100")
    dialog = BudgetDialog(app_services)
    offered = [dialog.category_combo.itemData(i) for i in range(dialog.category_combo.count())]
    assert offered == [other.id]
    dialog.deleteLater()
