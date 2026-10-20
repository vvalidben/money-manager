"""Loans on the Accounts page, and receipts on the Transactions page."""

from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QDialog

from money_manager.domain.entities import Account, TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.money import Money
from money_manager.services import AppServices
from money_manager.ui import dialogs
from money_manager.ui.accounts.accounts_page import AccountsPage
from money_manager.ui.debts.dialogs import DebtDialog, RepaymentDialog
from money_manager.ui.pages import PAGES
from money_manager.ui.transactions.receipts_dialog import ReceiptsDialog
from money_manager.ui.transactions.rows import PAPERCLIP
from money_manager.ui.transactions.transactions_page import TransactionsPage

ACCOUNTS = next(spec for spec in PAGES if spec.key == "accounts")
TRANSACTIONS = next(spec for spec in PAGES if spec.key == "transactions")
PNG = b"\x89PNG\r\n\x1a\n" + bytes(32)


@pytest.fixture
def bank(app_services: AppServices) -> Account:
    return app_services.accounts.create("Bank", opening_balance="5000",
                                        opening_date=date(2026, 1, 1))


@pytest.fixture
def accounts_page(qapp: QApplication, app_services: AppServices,
                  bank: Account) -> Iterator[AccountsPage]:
    page = AccountsPage(ACCOUNTS, app_services)
    page.resize(1200, 900)
    page.show()
    page.on_shown()
    yield page
    page.close()
    page.deleteLater()


def _auto(cls: type, fill, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: ANN001
    def run(dialog: QDialog) -> int:
        fill(dialog)
        return QDialog.DialogCode.Accepted if dialog.submit() else QDialog.DialogCode.Rejected

    monkeypatch.setattr(cls, "exec", run)


class TestLoans:
    def test_lend_repay_and_undo(self, accounts_page: AccountsPage, app_services: AppServices,
                                 bank: Account, monkeypatch: pytest.MonkeyPatch) -> None:
        card = accounts_page.loans_card
        assert card.empty_label.isVisibleTo(accounts_page)
        notices: list[tuple[str, str]] = []
        accounts_page.notice.connect(lambda t, d: notices.append((t, d)))

        def fill(dialog: DebtDialog) -> None:
            dialog.name_edit.setText("Sami")
            dialog.amount_edit.setText("1200")
            dialog.account_combo.setCurrentIndex(dialog.account_combo.findData(bank.id))

        _auto(DebtDialog, fill, monkeypatch)
        card.new_button.click()
        assert notices[-1] == ("Loan recorded", "Sami · 1,200.00 MAD")
        assert [card.table.item(0, c).text() for c in range(7)] == [
            "Sami", "Lent", "1,200.00 MAD", "0.00 MAD", "1,200.00 MAD", "—", "Open"]
        assert "Owed to you: 1,200.00 MAD" in card.summary_label.text()
        assert app_services.balances.balance(bank.id) == Money.of("3800")

        card.table.selectRow(0)
        _auto(RepaymentDialog, lambda d: d.amount_edit.setText("200"), monkeypatch)
        card.repay_button.click()
        assert notices[-1] == ("Repayment recorded", "Sami · 1,000.00 MAD left")
        assert card.table.item(0, 4).text() == "1,000.00 MAD"

        card.table.selectRow(0)
        monkeypatch.setattr(dialogs, "confirm_destructive", lambda *_a, **_k: True)
        card.undo_button.click()
        assert card.table.item(0, 4).text() == "1,200.00 MAD"
        assert app_services.balances.balance(bank.id) == Money.of("3800")

        card.table.selectRow(0)
        card.delete_button.click()
        assert app_services.debts.list() == [] and card.empty_label.isVisibleTo(accounts_page)

    def test_errors_stay_in_the_dialog(self, qapp: QApplication, app_services: AppServices,
                                       bank: Account) -> None:
        dialog = DebtDialog(app_services)
        dialog.amount_edit.setText("50")
        assert not dialog.submit()
        assert dialog.fields["name"].error_label.isVisibleTo(dialog)
        dialog.deleteLater()


@pytest.fixture
def expense(app_services: AppServices, bank: Account) -> int:
    food = app_services.categories.create("Food", CategoryKind.EXPENSE)
    return app_services.transactions.create(TransactionDraft(
        bank.id, TransactionType.EXPENSE, "45", date(2026, 6, 3), food.id,
        description="Market")).id


class TestReceipts:
    def test_attach_open_remove(self, qapp: QApplication, app_services: AppServices,
                                expense: int, tmp_path: Path,
                                monkeypatch: pytest.MonkeyPatch) -> None:
        (tmp_path / "ticket.png").write_bytes(PNG)
        transaction = app_services.transactions.get(expense)
        dialog = ReceiptsDialog(app_services, transaction)
        assert dialog.empty_label.isVisibleTo(dialog) or not dialog.isVisible()
        monkeypatch.setattr(dialogs, "ask_open_path", lambda *_a: tmp_path / "ticket.png")
        dialog.add_button.click()
        assert dialog.changed and dialog.list.count() == 1
        assert dialog.list.item(0).text().startswith("ticket.png")
        opened: list[Path] = []
        monkeypatch.setattr(dialog, "open_file", opened.append)
        dialog.open_button.click()
        assert opened and opened[0].read_bytes() == PNG
        monkeypatch.setattr(dialogs, "confirm_destructive", lambda *_a, **_k: True)
        dialog.remove_button.click()
        assert dialog.list.count() == 0
        dialog.deleteLater()

    def test_bad_file_is_explained(self, qapp: QApplication, app_services: AppServices,
                                   expense: int, tmp_path: Path,
                                   monkeypatch: pytest.MonkeyPatch) -> None:
        (tmp_path / "x.png").write_bytes(b"not an image")
        dialog = ReceiptsDialog(app_services, app_services.transactions.get(expense))
        monkeypatch.setattr(dialogs, "ask_open_path", lambda *_a: tmp_path / "x.png")
        dialog.add_button.click()
        assert "do not match" in dialog.status_label.text()
        dialog.deleteLater()

    def test_page_shows_the_paperclip(self, qapp: QApplication, app_services: AppServices,
                                      expense: int, tmp_path: Path,
                                      monkeypatch: pytest.MonkeyPatch) -> None:
        page = TransactionsPage(TRANSACTIONS, app_services)
        page.show()
        page.on_shown()
        try:
            assert page.model.row_at(0).description == "Market"
            page.table.selectRow(0)
            (tmp_path / "t.png").write_bytes(PNG)

            def fake(transaction):  # noqa: ANN001, ANN202
                app_services.receipts.add(transaction.id, tmp_path / "t.png")
                dialog = ReceiptsDialog(app_services, transaction, parent=page)
                dialog.changed = True
                monkeypatch.setattr(dialog, "exec", lambda: 0)
                return dialog

            monkeypatch.setattr(page, "make_receipts_dialog", fake)
            page.receipts_button.click()
            row = page.model.row_at(0)
            assert row.description == f"Market {PAPERCLIP}" and row.receipts == 1
            assert "1 receipt attached" in row.tooltip
        finally:
            page.close()
