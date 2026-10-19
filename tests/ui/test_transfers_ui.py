"""Transfers between accounts on the Transactions page."""

from collections.abc import Callable, Iterator
from datetime import date

import pytest
from PySide6.QtWidgets import QApplication, QDialog

from money_manager.domain.entities import Account
from money_manager.domain.money import Money
from money_manager.services import AppServices
from money_manager.ui import dialogs
from money_manager.ui.accounts.account_dialog import AccountDialog
from money_manager.ui.pages import PAGES, TRANSACTIONS_PAGE_KEY
from money_manager.ui.transactions.transactions_page import TransactionsPage
from money_manager.ui.transactions.transfer_dialog import TransferDialog
from tests.services.support import fixed_today

SPEC = next(spec for spec in PAGES if spec.key == TRANSACTIONS_PAGE_KEY)
OPENED = date(2026, 1, 1)


@pytest.fixture
def bank(app_services: AppServices) -> Account:
    return app_services.accounts.create("Bank", opening_balance="1000", opening_date=OPENED)


@pytest.fixture
def page(qapp: QApplication, app_services: AppServices, bank: Account) -> Iterator[TransactionsPage]:
    widget = TransactionsPage(SPEC, app_services)
    widget.resize(1200, 800)
    widget.show()
    widget.on_shown()
    yield widget
    widget.close()
    widget.deleteLater()


def _auto(monkeypatch: pytest.MonkeyPatch, dialog_type: type,
          fill: Callable[[QDialog], None]) -> None:
    def auto_submit(dialog: QDialog) -> int:
        fill(dialog)
        ok = dialog.submit()  # type: ignore[attr-defined]
        return QDialog.DialogCode.Accepted if ok else QDialog.DialogCode.Rejected

    monkeypatch.setattr(dialog_type, "exec", auto_submit)


def test_a_second_account_unlocks_transfers(page: TransactionsPage, app_services: AppServices,
                                            monkeypatch: pytest.MonkeyPatch) -> None:
    assert not page.transfer_button.isEnabled()

    def fill(dialog: QDialog) -> None:
        dialog.name_edit.setText("Cash wallet")  # type: ignore[attr-defined]
        dialog.balance_edit.setText("0")  # type: ignore[attr-defined]

    _auto(monkeypatch, AccountDialog, fill)
    notices: list[tuple[str, str]] = []
    page.notice.connect(lambda title, detail: notices.append((title, detail)))
    page.new_account_button.click()

    assert [a.name for a in app_services.accounts.list()] == ["Bank", "Cash wallet"]
    assert page.transfer_button.isEnabled()
    assert notices == [("Account created", "Cash wallet")]


def test_transfer_shows_both_sides_and_deletes_together(
        page: TransactionsPage, app_services: AppServices, bank: Account,
        monkeypatch: pytest.MonkeyPatch) -> None:
    cash = app_services.accounts.create("Cash wallet", opening_balance="0", opening_date=OPENED)
    page.reload()

    def fill(dialog: QDialog) -> None:
        assert isinstance(dialog, TransferDialog)
        dialog.to_combo.setCurrentIndex(dialog.to_combo.findData(cash.id))
        dialog.amount_edit.setText("300")

    _auto(monkeypatch, TransferDialog, fill)
    notices: list[tuple[str, str]] = []
    page.notice.connect(lambda title, detail: notices.append((title, detail)))
    page.transfer_button.click()

    assert notices == [("Transfer recorded", "300.00 MAD · Bank → Cash wallet")]
    rows = [page.model.row_at(r) for r in range(page.model.rowCount())]
    assert sorted((r.type, r.category) for r in rows) == [
        ("Transfer", "From Bank"), ("Transfer", "To Cash wallet")]
    assert app_services.balances.balance(cash.id) == Money.of("300")

    monkeypatch.setattr(dialogs, "confirm_destructive", lambda *_args: True)
    page.table.selectRow(0)
    page.delete_button.click()
    assert app_services.account_transfers.list() == []
    assert page.model.rowCount() == 0
    assert notices[-1] == ("Transfer deleted", "300.00 MAD · Bank → Cash wallet")


def test_a_transfer_side_cannot_be_edited(page: TransactionsPage, app_services: AppServices,
                                          bank: Account, monkeypatch: pytest.MonkeyPatch) -> None:
    cash = app_services.accounts.create("Cash wallet", opening_balance="0", opening_date=OPENED)
    app_services.account_transfers.create(bank.id, cash.id, "50", fixed_today())
    page.reload()
    shown: list[str] = []
    monkeypatch.setattr(dialogs, "show_info", lambda _p, title, _m: shown.append(title))
    monkeypatch.setattr(TransferDialog, "exec", lambda _self: pytest.fail("no dialog"))
    page.table.selectRow(0)
    page.edit_button.click()
    assert shown == ["Transfers cannot be edited"]


def test_dialog_shows_errors_next_to_the_field(qapp: QApplication, app_services: AppServices,
                                               bank: Account) -> None:
    app_services.accounts.create("Cash wallet", opening_balance="0", opening_date=OPENED)
    dialog = TransferDialog(app_services)
    dialog.to_combo.setCurrentIndex(0)  # same account as "From"
    dialog.amount_edit.setText("10")
    assert not dialog.submit()
    assert "two different accounts" in dialog.fields["to_account_id"].error
    assert app_services.account_transfers.list() == []
    dialog.deleteLater()
