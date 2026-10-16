from collections.abc import Iterator
from datetime import date

import pytest
from PySide6.QtWidgets import QApplication, QDialog

from money_manager.domain.entities import Account, Category
from money_manager.domain.enums import CategoryKind
from money_manager.domain.investments import EntryKind, InvestmentKind
from money_manager.domain.money import Money
from money_manager.services import AppServices
from money_manager.ui import dialogs
from money_manager.ui.investments.dialogs import EntryDialog, InvestmentDialog, ValueDialog
from money_manager.ui.investments.investments_page import InvestmentsPage
from money_manager.ui.investments.view_model import (
    entry_row,
    holding_row,
    position_status,
    summary_stats,
)
from money_manager.ui.pages import INVESTMENTS_PAGE_KEY, PAGES
from money_manager.ui.transactions.filter_bar import to_qdate
from tests.services.support import OPENING_DATE, TODAY

SPEC = next(spec for spec in PAGES if spec.key == INVESTMENTS_PAGE_KEY)


@pytest.fixture
def bank(app_services: AppServices) -> Account:
    return app_services.accounts.create("Bank", opening_balance="10000", opening_date=OPENING_DATE)


@pytest.fixture
def investing(app_services: AppServices) -> Category:
    category = app_services.categories.create("Investing", CategoryKind.EXPENSE)
    return app_services.categories.set_investment(category.id, True)


@pytest.fixture
def etf(app_services: AppServices, bank: Account, investing: Category):
    created = app_services.investments.create("World ETF", "etf")
    app_services.investments.add_contribution(created.investment.id, "1000", date(2026, 5, 1),
                                              account_id=bank.id, category_id=investing.id)
    app_services.investments.set_value(created.investment.id, "1100", date(2026, 6, 1))
    return app_services.investments.get(created.investment.id)


@pytest.fixture
def page(qapp: QApplication, app_services: AppServices) -> Iterator[InvestmentsPage]:
    widget = InvestmentsPage(SPEC, app_services)
    widget.resize(1200, 900)
    widget.show()
    widget.on_shown()
    yield widget
    widget.close()
    widget.deleteLater()


class TestViewModel:
    def test_holding_row(self, etf) -> None:
        assert holding_row(etf) == ("World ETF", "ETF", "1,000.00 MAD", "1,100.00 MAD",
                                    "+100.00 MAD", "+10.0%", "01 Jun 2026")
        assert position_status(etf) == "Return calculated from your latest value."

    def test_insufficient_data(self, app_services: AppServices) -> None:
        created = app_services.investments.create("Gold", "gold")
        app_services.investments.add_contribution(created.investment.id, "500", TODAY)
        item = app_services.investments.get(created.investment.id)

        assert holding_row(item)[3:6] == ("Not valued yet", "—", "—")
        assert "Enter the current value" in position_status(item)

        app_services.investments.set_value(created.investment.id, "450", date(2026, 6, 1))
        stale = app_services.investments.get(created.investment.id)
        assert holding_row(stale)[3:6] == ("450.00 MAD (out of date)", "—", "—")
        assert "update the value" in position_status(stale)

    def test_entry_row(self, etf) -> None:
        assert entry_row(etf.entries[0]) == ("01 May 2026", "Contribution",
                                             "Paid from your accounts", "", "+1,000.00 MAD")

    def test_summary(self, app_services: AppServices, etf) -> None:
        stats = summary_stats(app_services.investments.summary())

        assert [s.value for s in stats] == ["1,100.00 MAD", "1,000.00 MAD", "+100.00 MAD",
                                            "10,100.00 MAD"]
        assert stats[2].caption == "+10.0% · 1 of 1 up to date"
        assert stats[3].caption == "Balance 9,000.00 MAD + investments"

    def test_summary_without_values(self, app_services: AppServices) -> None:
        created = app_services.investments.create("Gold", "gold")
        app_services.investments.add_contribution(created.investment.id, "500", TODAY)

        profit = summary_stats(app_services.investments.summary())[2]

        assert profit.value == "—" and "Update the values" in profit.caption


class TestDialogs:
    def test_create_investment(self, qapp: QApplication, app_services: AppServices) -> None:
        dialog = InvestmentDialog(app_services)
        dialog.name_edit.setText("Bitcoin")
        dialog.kind_combo.setCurrentIndex(dialog.kind_combo.findData("crypto"))

        assert dialog.submit()
        assert dialog.saved is not None and dialog.saved.investment.kind is InvestmentKind.CRYPTO

    def test_paid_contribution(self, qapp: QApplication, app_services: AppServices, etf,
                               bank: Account) -> None:
        dialog = EntryDialog(app_services, etf, EntryKind.CONTRIBUTION)
        assert dialog.from_account_check.isChecked()  # accounts exist
        dialog.amount_edit.setText("500")

        assert dialog.submit()
        assert app_services.balances.balance(bank.id) == Money.of("8500")
        assert app_services.investments.get(etf.investment.id).contributed == Money.of("1500")

    def test_external_contribution(self, qapp: QApplication, app_services: AppServices, etf,
                                   bank: Account) -> None:
        dialog = EntryDialog(app_services, etf, EntryKind.CONTRIBUTION)
        dialog.from_account_check.setChecked(False)
        dialog.amount_edit.setText("300")

        assert dialog.fields["account_id"].isHidden()
        assert dialog.submit()
        assert app_services.balances.balance(bank.id) == Money.of("9000")  # unchanged

    def test_errors_inline(self, qapp: QApplication, app_services: AppServices, etf) -> None:
        dialog = EntryDialog(app_services, etf, EntryKind.CONTRIBUTION)
        dialog.amount_edit.setText("0")

        assert not dialog.submit()
        assert dialog.fields["amount"].error == "Amount must be greater than zero."

    def test_new_investment_category_inline(self, qapp: QApplication, app_services: AppServices,
                                            bank: Account) -> None:
        created = app_services.investments.create("Gold", "gold")
        dialog = EntryDialog(app_services, created, EntryKind.CONTRIBUTION)
        assert dialog.category_combo.count() == 0

        dialog.create_category("Gold purchases")

        assert dialog.category_combo.currentText() == "Gold purchases"
        category_id = dialog.category_combo.currentData()
        assert app_services.categories.get(category_id).is_investment

    def test_withdrawal(self, qapp: QApplication, app_services: AppServices, etf) -> None:
        dialog = EntryDialog(app_services, etf, EntryKind.WITHDRAWAL)
        dialog.amount_edit.setText("200")

        assert dialog.submit()
        assert app_services.investments.get(etf.investment.id).net_invested == Money.of("800")

    def test_value_dialog(self, qapp: QApplication, app_services: AppServices, etf) -> None:
        dialog = ValueDialog(app_services, etf)
        assert dialog.value_edit.text() == "1100.00"
        dialog.value_edit.setText("1 250")
        dialog.date_edit.setDate(to_qdate(TODAY))

        assert dialog.submit()
        assert app_services.investments.get(etf.investment.id).profit == Money.of("250")


class TestPage:
    def test_empty_state(self, page: InvestmentsPage) -> None:
        assert not page.empty_state.isHidden() and page.holdings_card.isHidden()

    def test_holdings_and_details(self, page: InvestmentsPage, etf) -> None:
        page.refresh()

        assert page.table.rowCount() == 1
        assert page.selected() is not None
        assert page.detail_title.text() == "World ETF · ETF"
        assert page.entries_card.cell(0, 4) == "+1,000.00 MAD"
        assert page.values_card.cell(0, 1) == "1,100.00 MAD"
        assert page.stat_cards[0].value == "1,100.00 MAD"

    def test_delete_linked_entry_removes_the_expense(
        self, page: InvestmentsPage, app_services: AppServices, etf, bank: Account,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        page.refresh()
        monkeypatch.setattr(dialogs, "confirm_destructive", lambda *_args: True)

        page.entries_card.table.selectRow(0)
        page.delete_entry_button.click()

        assert app_services.transactions.list() == []
        assert app_services.balances.balance(bank.id) == Money.of("10000")
        assert page.entries_card.table.rowCount() == 0

    def test_archive_and_show_archived(self, page: InvestmentsPage, etf) -> None:
        page.refresh()
        page.archive_button.click()

        assert page.table.rowCount() == 0
        page.show_archived.setChecked(True)
        assert page.table.rowCount() == 1
        assert page.table.item(0, 0).text() == "World ETF (archived)"
        assert not page.contribute_button.isEnabled()
        assert page.archive_button.text() == "Restore"

    def test_add_contribution_from_page(self, page: InvestmentsPage, app_services: AppServices,
                                        etf, monkeypatch: pytest.MonkeyPatch) -> None:
        page.refresh()

        def submit(dialog: EntryDialog) -> int:
            dialog.amount_edit.setText("250")
            dialog.from_account_check.setChecked(False)
            return QDialog.DialogCode.Accepted if dialog.submit() else QDialog.DialogCode.Rejected

        monkeypatch.setattr(EntryDialog, "exec", submit)
        page.contribute_button.click()

        assert page.table.item(0, 2).text() == "1,250.00 MAD"
        assert "out of date" in page.table.item(0, 3).text()  # value predates the contribution

    def test_delete_investment(self, page: InvestmentsPage, app_services: AppServices, etf,
                               monkeypatch: pytest.MonkeyPatch) -> None:
        page.refresh()
        monkeypatch.setattr(dialogs, "confirm_destructive", lambda *_args: True)

        page.delete_button.click()

        assert app_services.investments.list(include_archived=True) == []
        assert len(app_services.transactions.list()) == 1  # the real expense stays
        assert not page.empty_state.isHidden()
