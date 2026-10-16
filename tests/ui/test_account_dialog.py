import pytest
from PySide6.QtWidgets import QApplication

from money_manager.domain.money import Money
from money_manager.services import AppServices
from money_manager.ui.accounts.account_dialog import AccountDialog
from tests.services.support import TODAY


def test_create_account(qapp: QApplication, app_services: AppServices) -> None:
    dialog = AccountDialog(app_services)
    dialog.name_edit.setText("Cash")
    dialog.balance_edit.setText("-150,75")

    assert dialog.submit()

    assert dialog.saved is not None
    assert dialog.saved.opening_balance == Money.of("-150.75")
    assert dialog.saved.opening_date == TODAY


@pytest.mark.parametrize(
    ("name", "balance", "field", "message"),
    [
        ("", "0", "name", "cannot be empty"),
        ("Cash", "1.200", "opening_balance", "ambiguous"),
        ("Cash", "", "opening_balance", "Enter an amount"),
    ],
)
def test_errors_inline(
    qapp: QApplication, app_services: AppServices, name: str, balance: str, field: str,
    message: str,
) -> None:
    dialog = AccountDialog(app_services)
    dialog.name_edit.setText(name)
    dialog.balance_edit.setText(balance)

    assert not dialog.submit()

    assert message in dialog.fields[field].error
    assert app_services.accounts.list() == []


def test_duplicate_name_uses_form_banner(qapp: QApplication, app_services: AppServices) -> None:
    app_services.accounts.create("Cash")
    dialog = AccountDialog(app_services)
    dialog.name_edit.setText("cash")

    assert not dialog.submit()

    assert "already exists" in dialog.form_error.text()
    assert not dialog.form_error.isHidden()
