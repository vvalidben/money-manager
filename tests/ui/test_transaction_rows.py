from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

from money_manager.domain.entities import Transaction
from money_manager.domain.enums import TransactionSort, TransactionType
from money_manager.domain.money import Money
from money_manager.ui.formatting import format_date, format_money, format_signed_money
from money_manager.ui.theme import Colors
from money_manager.ui.transactions.rows import NO_CATEGORY, NO_DESCRIPTION, build_rows
from money_manager.ui.transactions.table_model import Column, TransactionTableModel


def _tx(type_: TransactionType, amount: str, **kw: object) -> Transaction:
    fields: dict[str, object] = {
        "id": 1, "account_id": 1, "type": type_, "amount": Money.of(amount),
        "occurred_on": date(2026, 3, 5), "category_id": 7, "description": "Lunch", "notes": "",
    }
    fields.update(kw)
    return Transaction(**fields)  # type: ignore[arg-type]


def test_money_formatting() -> None:
    assert format_money(Money.of("12000")) == "12,000.00 MAD"
    assert format_money(Money.of("-300.5")) == "−300.50 MAD"
    assert format_signed_money(Money.of("5")) == "+5.00 MAD"
    assert format_signed_money(Money.of("-5")) == "−5.00 MAD"
    assert format_signed_money(Money.zero()) == "0.00 MAD"
    assert format_date(date(2026, 3, 5)) == "05 Mar 2026"


def test_rows_show_direction_from_the_domain() -> None:
    income, expense = build_rows(
        [_tx(TransactionType.INCOME, "12000", id=1), _tx(TransactionType.EXPENSE, "300", id=2)],
        {7: "Food"},
        {},
    )

    assert (income.amount, income.is_inflow, income.type) == ("+12,000.00 MAD", True, "Income")
    assert (expense.amount, expense.is_inflow, expense.type) == ("−300.00 MAD", False, "Expense")
    assert expense.category == "Food"
    assert expense.date == "05 Mar 2026"


def test_row_placeholders_and_tooltip() -> None:
    [row] = build_rows(
        [_tx(TransactionType.EXPENSE, "1", category_id=None, description="", notes="card",
             allocation_id=3, type=TransactionType.EXPENSE)],
        {},
        {3: "Bills"},
    )
    assert row.description == NO_DESCRIPTION
    assert row.category == NO_CATEGORY
    assert row.tooltip == "Paid from: Bills\ncard"


def test_table_model_roles(qapp: QApplication) -> None:
    model = TransactionTableModel()
    model.set_rows(build_rows(
        [_tx(TransactionType.INCOME, "10", id=1), _tx(TransactionType.EXPENSE, "3", id=2)],
        {7: "Food"}, {},
    ))

    assert (model.rowCount(), model.columnCount()) == (2, 5)
    assert model.headerData(Column.AMOUNT, Qt.Orientation.Horizontal) == "Amount"
    income_amount = model.index(0, Column.AMOUNT)
    expense_amount = model.index(1, Column.AMOUNT)
    assert model.data(income_amount) == "+10.00 MAD"
    assert model.data(income_amount, Qt.ItemDataRole.ForegroundRole) == QColor(Colors.INFLOW)
    assert model.data(expense_amount, Qt.ItemDataRole.ForegroundRole) == QColor(Colors.OUTFLOW)
    assert model.data(income_amount, Qt.ItemDataRole.TextAlignmentRole) & Qt.AlignmentFlag.AlignRight
    assert model.data(model.index(1, 0), Qt.ItemDataRole.UserRole).id == 2
    assert model.row_of(2) == 1 and model.row_of(99) is None


def test_table_model_reports_sort_requests(qapp: QApplication) -> None:
    model = TransactionTableModel()
    requests: list[tuple[TransactionSort, bool]] = []
    model.sort_requested.connect(lambda sort, desc: requests.append((sort, desc)))

    model.sort(Column.AMOUNT, Qt.SortOrder.AscendingOrder)
    model.sort(Column.CATEGORY, Qt.SortOrder.DescendingOrder)

    assert requests == [(TransactionSort.AMOUNT, False), (TransactionSort.CATEGORY, True)]
