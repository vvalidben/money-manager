from datetime import date

import pytest
from PySide6.QtWidgets import QApplication

from money_manager.domain.entities import Account, Category, TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.money import Money
from money_manager.services import AppServices
from money_manager.ui import dialogs
from money_manager.ui.transactions.filter_bar import to_qdate
from money_manager.ui.transactions.transaction_dialog import TransactionDialog
from tests.services.support import OPENING_DATE, TODAY


@pytest.fixture
def account(app_services: AppServices) -> Account:
    return app_services.accounts.create("Bank", opening_balance="1000", opening_date=OPENING_DATE)


@pytest.fixture
def food(app_services: AppServices) -> Category:
    return app_services.categories.create("Food", CategoryKind.EXPENSE)


@pytest.fixture
def salary(app_services: AppServices) -> Category:
    return app_services.categories.create("Salary", CategoryKind.INCOME)


def _dialog(app_services: AppServices, **kwargs: object) -> TransactionDialog:
    return TransactionDialog(app_services, **kwargs)  # type: ignore[arg-type]


def _select_type(dialog: TransactionDialog, transaction_type: TransactionType) -> None:
    dialog.type_combo.setCurrentIndex(dialog.type_combo.findData(transaction_type))


def test_add_expense(
    qapp: QApplication, app_services: AppServices, account: Account, food: Category
) -> None:
    dialog = _dialog(app_services)
    dialog.amount_edit.setText("1 250,50")
    dialog.description_edit.setText("  Groceries ")
    dialog.date_edit.setDate(to_qdate(date(2026, 6, 1)))

    assert dialog.submit()

    saved = dialog.saved
    assert saved is not None
    assert (saved.type, saved.amount, saved.category_id) == (
        TransactionType.EXPENSE, Money.of("1250.50"), food.id
    )
    assert (saved.occurred_on, saved.description) == (date(2026, 6, 1), "Groceries")
    assert app_services.balances.total_balance() == Money.of("-250.50")


def test_defaults(qapp: QApplication, app_services: AppServices, account: Account, food: Category) -> None:
    dialog = _dialog(app_services)

    assert dialog.selected_type is TransactionType.EXPENSE
    assert dialog.date_edit.date().toPython() == TODAY
    assert dialog.date_edit.maximumDate().toPython() == TODAY
    assert dialog.date_edit.minimumDate().toPython() == OPENING_DATE
    assert dialog.category_combo.currentData() == food.id
    assert dialog.allocation_combo.currentData() is None
    assert dialog.fields["account_id"].isHidden()  # only one account


def test_category_list_follows_type(
    qapp: QApplication, app_services: AppServices, account: Account, food: Category,
    salary: Category,
) -> None:
    dialog = _dialog(app_services)

    _select_type(dialog, TransactionType.INCOME)
    assert [dialog.category_combo.itemData(i) for i in range(dialog.category_combo.count())] == [
        salary.id
    ]
    assert dialog.fields["allocation_id"].label.text() == "Put into"

    _select_type(dialog, TransactionType.ADJUSTMENT_OUT)
    dialog.amount_edit.setText("5")
    assert dialog.fields["category_id"].isHidden()
    assert dialog.fields["allocation_id"].isHidden()
    draft = dialog.build_draft()
    assert (draft.category_id, draft.allocation_id) == (None, None)


@pytest.mark.parametrize(
    ("amount", "message"),
    [
        ("", "Enter an amount"),
        ("0", "greater than zero"),
        ("1,200", "ambiguous"),
    ],
)
def test_amount_errors_are_shown_inline(
    qapp: QApplication, app_services: AppServices, account: Account, food: Category,
    amount: str, message: str,
) -> None:
    dialog = _dialog(app_services)
    dialog.amount_edit.setText(amount)

    assert not dialog.submit()

    assert message in dialog.fields["amount"].error
    assert dialog.fields["amount"].widget.property("invalid") is True
    assert app_services.transactions.list() == []
    dialog.amount_edit.setText("5")
    assert dialog.fields["amount"].error == ""  # cleared as soon as the user edits


def test_missing_category_is_shown_on_the_category_field(
    qapp: QApplication, app_services: AppServices, account: Account
) -> None:
    dialog = _dialog(app_services)  # no expense categories exist yet
    dialog.amount_edit.setText("10")

    assert not dialog.submit()

    assert "Choose a category" in dialog.fields["category_id"].error


def test_allocation_shortfall_is_shown_on_the_allocation_field(
    qapp: QApplication, app_services: AppServices, account: Account, food: Category
) -> None:
    bills = app_services.allocations.create("Bills")
    dialog = _dialog(app_services)
    dialog.amount_edit.setText("10")
    dialog.allocation_combo.setCurrentIndex(dialog.allocation_combo.findData(bills.id))

    assert not dialog.submit()  # Bills holds nothing

    assert "Bills" in dialog.fields["allocation_id"].error


def test_create_category_inline(
    qapp: QApplication, app_services: AppServices, account: Account
) -> None:
    dialog = _dialog(app_services)
    _select_type(dialog, TransactionType.INCOME)

    created = dialog.create_category("Freelance")

    assert created is not None and created.kind is CategoryKind.INCOME
    assert dialog.category_combo.currentData() == created.id


def test_create_duplicate_category_warns(
    qapp: QApplication, app_services: AppServices, account: Account, food: Category,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    warnings: list[str] = []
    monkeypatch.setattr(dialogs, "show_warning", lambda _p, _t, message: warnings.append(message))
    dialog = _dialog(app_services)

    assert dialog.create_category("food") is None
    assert warnings and "already exists" in warnings[0]


def test_edit_prefills_and_updates(
    qapp: QApplication, app_services: AppServices, account: Account, food: Category,
    salary: Category,
) -> None:
    original = app_services.transactions.create(
        TransactionDraft(account.id, TransactionType.EXPENSE, "300", date(2026, 5, 1), food.id,
                         description="Lunch", notes="team")
    )
    dialog = _dialog(app_services, transaction=original)

    assert dialog.windowTitle() == "Edit transaction"
    assert dialog.amount_edit.text() == "300.00"
    assert dialog.description_edit.text() == "Lunch"
    assert dialog.notes_edit.toPlainText() == "team"
    assert dialog.date_edit.date().toPython() == date(2026, 5, 1)
    assert dialog.category_combo.currentData() == food.id

    _select_type(dialog, TransactionType.INCOME)
    dialog.amount_edit.setText("450")
    assert dialog.submit()

    updated = app_services.transactions.get(original.id)
    assert (updated.type, updated.amount, updated.category_id) == (
        TransactionType.INCOME, Money.of("450"), salary.id
    )
    assert app_services.balances.total_balance() == Money.of("1450")


def test_edit_keeps_archived_category(
    qapp: QApplication, app_services: AppServices, account: Account, food: Category
) -> None:
    original = app_services.transactions.create(
        TransactionDraft(account.id, TransactionType.EXPENSE, "10", TODAY, food.id)
    )
    app_services.categories.archive(food.id)

    dialog = _dialog(app_services, transaction=original)
    dialog.amount_edit.setText("11")

    assert dialog.category_combo.currentData() == food.id
    assert dialog.submit()
