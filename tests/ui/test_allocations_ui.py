"""Money / Allocations page: set money aside, move it, archive, undo."""

from collections.abc import Callable, Iterator
from datetime import date

import pytest
from PySide6.QtWidgets import QApplication, QDialog

from money_manager.domain.entities import TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.money import Money
from money_manager.services import AppServices
from money_manager.ui import dialogs
from money_manager.ui.allocations.allocations_page import AllocationsPage
from money_manager.ui.allocations.dialogs import AllocationDialog, MoveMoneyDialog
from money_manager.ui.pages import ALLOCATIONS_PAGE_KEY, PAGES
from tests.services.support import fixed_today

SPEC = next(spec for spec in PAGES if spec.key == ALLOCATIONS_PAGE_KEY)


@pytest.fixture
def funded(app_services: AppServices) -> AppServices:
    app_services.accounts.create("Bank", opening_balance="1000", opening_date=date(2026, 1, 1))
    return app_services


@pytest.fixture
def page(qapp: QApplication, funded: AppServices) -> Iterator[AllocationsPage]:
    widget = AllocationsPage(SPEC, funded)
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


def _notices(page: AllocationsPage) -> list[tuple[str, str]]:
    seen: list[tuple[str, str]] = []
    page.notice.connect(lambda title, detail: seen.append((title, detail)))
    return seen


def test_create_with_money_set_aside(page: AllocationsPage, funded: AppServices,
                                     monkeypatch: pytest.MonkeyPatch) -> None:
    assert page.empty_state.isVisible()

    def fill(dialog: QDialog) -> None:
        dialog.name_edit.setText("Bills")  # type: ignore[attr-defined]
        dialog.amount_edit.setText("400")  # type: ignore[attr-defined]

    _auto(monkeypatch, AllocationDialog, fill)
    notices = _notices(page)
    page.empty_state.action_button.click()

    [card] = page.cards
    assert (card.view.name, card.view.balance) == ("Bills", "400.00 MAD")
    assert card.view.share == "40.0% of your total balance"
    assert [c.value for c in page.stat_cards] == ["600.00 MAD", "1,000.00 MAD",
                                                  "400.00 MAD", "1"]
    assert notices == [("Allocation created", "Bills")]


def test_add_and_take_out_money(page: AllocationsPage, funded: AppServices,
                                monkeypatch: pytest.MonkeyPatch) -> None:
    bills = funded.allocations.create("Bills", initial_amount="100")
    page.refresh()

    def add(dialog: QDialog) -> None:
        assert dialog.from_combo.currentData() is None  # type: ignore[attr-defined]
        assert dialog.to_combo.currentData() == bills.id  # type: ignore[attr-defined]
        dialog.amount_edit.setText("250")  # type: ignore[attr-defined]

    _auto(monkeypatch, MoveMoneyDialog, add)
    notices = _notices(page)
    page.move_money(None, bills.id)
    assert funded.allocations.balance(bills.id) == Money.of("350")
    assert notices == [("Money moved", "250.00 MAD · Available → Bills")]

    def take(dialog: QDialog) -> None:
        dialog.amount_edit.setText("5000")  # type: ignore[attr-defined]

    _auto(monkeypatch, MoveMoneyDialog, take)
    page.move_money(bills.id, None)  # more than it holds: refused, nothing changes
    assert funded.allocations.balance(bills.id) == Money.of("350")


def test_goal_money_is_managed_from_the_goal(page: AllocationsPage,
                                             funded: AppServices) -> None:
    funded.goals.create_with_new_allocation("Car", target="5000", initial_amount="300")
    page.refresh()
    [card] = page.cards
    assert card.view.goal == "Backs the goal Car"
    assert not card.archive_button.isEnabled()


def test_archive_restore_and_undo(page: AllocationsPage, funded: AppServices,
                                  monkeypatch: pytest.MonkeyPatch) -> None:
    trip = funded.allocations.create("Trip", initial_amount="200")
    page.refresh()
    monkeypatch.setattr(dialogs, "confirm_destructive", lambda *_args: True)

    page.archive_allocation(trip.id)
    assert funded.allocations.available() == Money.of("1000")
    assert page.cards == [] and [a.name for a in page.archived] == ["Trip"]

    page.restore(trip.id)
    assert [c.view.name for c in page.cards] == ["Trip"]

    funded.transfers.transfer(from_allocation_id=None, to_allocation_id=trip.id, amount="50")
    page.refresh()
    newest = page.moves[0]
    assert newest.route == "Available → Trip" and newest.amount == "50.00 MAD"
    page.undo_move(newest.transfer_id)
    assert funded.allocations.balance(trip.id) == Money.of("0")


def test_over_allocation_is_explained(page: AllocationsPage, funded: AppServices) -> None:
    funded.allocations.create("Bills", initial_amount="900")
    bank = funded.accounts.list()[0]
    food = funded.categories.create("Food", CategoryKind.EXPENSE)
    funded.transactions.create(TransactionDraft(bank.id, TransactionType.EXPENSE, "300",
                                                fixed_today(), food.id))
    page.refresh()
    assert not page.warning.isHidden()
    assert "short by 200.00 MAD" in page.warning.text()
    assert page.stat_cards[0].value == "−200.00 MAD"
