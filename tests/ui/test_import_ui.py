"""Importing a bank statement from the Transactions page."""

from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QDialog

from money_manager.domain.entities import Account
from money_manager.domain.enums import CategoryKind
from money_manager.domain.money import Money
from money_manager.services import AppServices
from money_manager.ui import dialogs
from money_manager.ui.pages import PAGES, TRANSACTIONS_PAGE_KEY
from money_manager.ui.transactions.import_dialog import ImportStatementDialog
from money_manager.ui.transactions.transactions_page import TransactionsPage
from tests.services.support import fixed_today

SPEC = next(spec for spec in PAGES if spec.key == TRANSACTIONS_PAGE_KEY)
D = fixed_today().strftime("%d/%m/%Y")


@pytest.fixture
def bank(app_services: AppServices) -> Account:
    app_services.categories.create("Groceries", CategoryKind.EXPENSE)
    app_services.categories.create("Salary", CategoryKind.INCOME)
    return app_services.accounts.create("Bank", opening_balance="1000",
                                        opening_date=fixed_today() - timedelta(days=30))


@pytest.fixture
def statement(tmp_path: Path) -> Path:
    path = tmp_path / "octobre.csv"
    path.write_text(f"Date opération;Date de valeur;Libellé;Débit;Crédit\n"
                    f"{D};{D};CB MARJANE;642,30;\n{D};{D};VIREMENT SALAIRE;;14 500,00\n"
                    f"oops;;;;\n", encoding="cp1252")
    return path


@pytest.fixture
def page(qapp: QApplication, app_services: AppServices, bank: Account) -> Iterator[TransactionsPage]:
    widget = TransactionsPage(SPEC, app_services)
    widget.resize(1200, 800)
    widget.show()
    widget.on_shown()
    yield widget
    widget.close()
    widget.deleteLater()


def test_dialog_detects_columns_and_previews(qapp: QApplication, app_services: AppServices,
                                             bank: Account, statement: Path) -> None:
    table = app_services.statements.read(statement)
    dialog = ImportStatementDialog(app_services, statement, table)
    assert dialog.mode_combo.currentData() == "two"
    assert dialog.description_combo.currentText() == "Libellé"
    assert dialog.debit_combo.currentText() == "Débit"
    assert dialog.format_combo.currentData() == "%d/%m/%Y"
    assert dialog.summary_label.text() == "2 new · 0 already recorded · 1 cannot be read"
    assert dialog.import_button.text() == "Import 2 entries"
    statuses = [dialog.table.item(r, 4).text() for r in range(dialog.table.rowCount())]
    assert statuses == ["New", "New", "'oops' is not a date."]
    dialog.deleteLater()


def test_page_imports_and_reports(page: TransactionsPage, app_services: AppServices,
                                  bank: Account, statement: Path,
                                  monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(page, "ask_statement_path", lambda: statement)

    def auto(dialog: ImportStatementDialog) -> int:
        return QDialog.DialogCode.Accepted if dialog.submit() else QDialog.DialogCode.Rejected

    monkeypatch.setattr(ImportStatementDialog, "exec", auto)
    notices: list[tuple[str, str]] = []
    page.notice.connect(lambda title, detail: notices.append((title, detail)))
    page.import_button.click()

    assert notices == [("Statement imported", "2 added · 0 already recorded")]
    assert app_services.balances.balance(bank.id) == Money.of("14857.70")
    assert page.model.rowCount() == 2

    page.import_button.click()  # the same file again: nothing new, so nothing is imported
    assert len(app_services.transactions.list()) == 2
    assert len(notices) == 1


def test_unreadable_file_is_explained(page: TransactionsPage, tmp_path: Path,
                                      monkeypatch: pytest.MonkeyPatch) -> None:
    empty = tmp_path / "empty.csv"
    empty.write_text("", encoding="utf-8")
    monkeypatch.setattr(page, "ask_statement_path", lambda: empty)
    warnings: list[str] = []
    monkeypatch.setattr(dialogs, "show_warning", lambda _p, title, _m: warnings.append(title))
    page.import_button.click()
    assert warnings == ["Could not read the statement"]
