"""Accounts page: list, create, edit, correct the balance, delete."""

from collections.abc import Callable, Iterator
from datetime import date

import pytest
from PySide6.QtWidgets import QApplication, QDialog

from money_manager.domain.entities import TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.money import Money
from money_manager.services import AppServices
from money_manager.ui import dialogs
from money_manager.ui.accounts.account_dialog import AccountDialog
from money_manager.ui.accounts.accounts_page import AccountsPage
from money_manager.ui.accounts.correct_balance_dialog import CorrectBalanceDialog
from money_manager.ui.pages import ACCOUNTS_PAGE_KEY, PAGES
from tests.services.support import fixed_today

SPEC = next(spec for spec in PAGES if spec.key == ACCOUNTS_PAGE_KEY)
OPENED = date(2026, 1, 1)


@pytest.fixture
def page(qapp: QApplication, app_services: AppServices) -> Iterator[AccountsPage]:
    widget = AccountsPage(SPEC, app_services)
    widget.resize(1100, 800)
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


def _notices(page: AccountsPage) -> list[tuple[str, str]]:
    seen: list[tuple[str, str]] = []
    page.notice.connect(lambda title, detail: seen.append((title, detail)))
    return seen


def test_empty_state_then_create(page: AccountsPage, app_services: AppServices,
                                 monkeypatch: pytest.MonkeyPatch) -> None:
    assert page.empty_state.isVisible() and not page.new_button.isVisible()

    def fill(dialog: QDialog) -> None:
        dialog.name_edit.setText("Bank")  # type: ignore[attr-defined]
        dialog.balance_edit.setText("2500.50")  # type: ignore[attr-defined]

    _auto(monkeypatch, AccountDialog, fill)
    notices = _notices(page)
    page.empty_state.action_button.click()

    assert notices == [("Account created", "Bank")]
    card = page.card_for(app_services.accounts.list()[0].id)
    assert card.view.balance == "2,500.50 MAD" and card.view.share == "100.0% of what you have"
    assert not page.transfer_button.isEnabled()  # needs a second account


def test_summary_and_cards_largest_first(page: AccountsPage, app_services: AppServices) -> None:
    app_services.accounts.create("Bank", opening_balance="9000", opening_date=OPENED)
    app_services.accounts.create("Card", opening_balance="-1200", opening_date=OPENED)
    app_services.accounts.create("Cash", opening_balance="1000", opening_date=OPENED)
    page.refresh()
    assert [c.view.name for c in page.cards] == ["Bank", "Cash", "Card"]
    assert [c.value for c in page.stat_cards] == ["8,800.00 MAD", "10,000.00 MAD",
                                                  "1,200.00 MAD", "3"]
    assert page.card_for(page.cards[2].view.account_id).view.share == "Owed"
    assert page.transfer_button.isEnabled()


def test_edit_renames(page: AccountsPage, app_services: AppServices,
                      monkeypatch: pytest.MonkeyPatch) -> None:
    bank = app_services.accounts.create("Bank", opening_balance="100", opening_date=OPENED)
    page.refresh()

    def fill(dialog: QDialog) -> None:
        assert dialog.name_edit.text() == "Bank"  # type: ignore[attr-defined]
        dialog.name_edit.setText("CIH Bank")  # type: ignore[attr-defined]

    _auto(monkeypatch, AccountDialog, fill)
    notices = _notices(page)
    page.edit_account(bank.id)
    assert app_services.accounts.get(bank.id).name == "CIH Bank"
    assert app_services.accounts.get(bank.id).opening_balance == Money.of("100")
    assert notices == [("Account updated", "CIH Bank")]


def test_correct_balance_records_an_adjustment(page: AccountsPage, app_services: AppServices,
                                               monkeypatch: pytest.MonkeyPatch) -> None:
    bank = app_services.accounts.create("Bank", opening_balance="1000", opening_date=OPENED)
    page.refresh()

    def fill(dialog: QDialog) -> None:
        assert dialog.balance_edit.text() == "1000.00"  # type: ignore[attr-defined]
        dialog.balance_edit.setText("950.25")  # type: ignore[attr-defined]

    _auto(monkeypatch, CorrectBalanceDialog, fill)
    notices = _notices(page)
    page.correct_balance(bank.id)
    assert app_services.balances.balance(bank.id) == Money.of("950.25")
    assert notices == [("Balance corrected", "Bank · adjustment −49.75 MAD")]
    [adjustment] = app_services.transactions.list()
    assert adjustment.type is TransactionType.ADJUSTMENT_OUT


def test_delete_only_unused_accounts(page: AccountsPage, app_services: AppServices,
                                     monkeypatch: pytest.MonkeyPatch) -> None:
    used = app_services.accounts.create("Bank", opening_balance="100", opening_date=OPENED)
    unused = app_services.accounts.create("Old card", opening_balance="0", opening_date=OPENED)
    food = app_services.categories.create("Food", CategoryKind.EXPENSE)
    app_services.transactions.create(TransactionDraft(used.id, TransactionType.EXPENSE, "5",
                                                      fixed_today(), food.id))
    page.refresh()
    monkeypatch.setattr(dialogs, "confirm_destructive", lambda *_args: True)
    warnings: list[str] = []
    monkeypatch.setattr(dialogs, "show_warning", lambda _p, _t, message: warnings.append(message))

    page.delete_account(used.id)
    assert warnings and len(app_services.accounts.list()) == 2

    page.delete_account(unused.id)
    assert [a.name for a in app_services.accounts.list()] == ["Bank"]


def test_accounts_need_two_for_a_transfer(page: AccountsPage,
                                          app_services: AppServices) -> None:
    app_services.accounts.create("Bank", opening_balance="100", opening_date=OPENED)
    page.refresh()
    assert page.transfer_button.isVisible() and not page.transfer_button.isEnabled()
