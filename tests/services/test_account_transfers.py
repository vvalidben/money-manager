"""Transfers between the user's own accounts."""

from datetime import date, timedelta
from pathlib import Path

import pytest

from money_manager.core.errors import ConflictError, NotFoundError, ValidationError
from money_manager.domain.entities import Account, TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.money import Money
from money_manager.services import AppServices
from money_manager.services.data_service import RESET_CONFIRMATION
from tests.services.support import fixed_today

OPENED = date(2026, 1, 1)


@pytest.fixture
def bank(app_services: AppServices) -> Account:
    return app_services.accounts.create("Bank", opening_balance="1000", opening_date=OPENED)


@pytest.fixture
def cash(app_services: AppServices) -> Account:
    return app_services.accounts.create("Cash wallet", opening_balance="0", opening_date=OPENED)


def test_a_transfer_moves_money_without_changing_the_total(
        app_services: AppServices, bank: Account, cash: Account) -> None:
    transfer = app_services.account_transfers.create(bank.id, cash.id, "300", fixed_today())

    balances = app_services.balances
    assert balances.balance(bank.id) == Money.of("700")
    assert balances.balance(cash.id) == Money.of("300")
    assert balances.total_balance() == Money.of("1000")
    assert (transfer.from_account_id, transfer.to_account_id) == (bank.id, cash.id)
    assert transfer.amount == Money.of("300")
    out, into = (app_services.transactions.get(transfer.out_transaction_id),
                 app_services.transactions.get(transfer.in_transaction_id))
    assert (out.type, into.type) == (TransactionType.ADJUSTMENT_OUT, TransactionType.ADJUSTMENT_IN)
    assert (out.description, into.description) == ("Transfer to Cash wallet",
                                                   "Transfer from Bank")


def test_a_transfer_is_never_income_or_spending(app_services: AppServices, bank: Account,
                                                cash: Account) -> None:
    app_services.account_transfers.create(bank.id, cash.id, "300", fixed_today(),
                                          description="Cash for the market")
    overview = app_services.dashboard.overview()
    assert overview.income == Money.of("0") and overview.expenses == Money.of("0")
    assert app_services.allocations.check_consistency().is_consistent


@pytest.mark.parametrize(("amount", "field"), [("0", "amount"), ("-5", "amount"),
                                               ("1.234", "amount")])
def test_invalid_amounts_create_nothing(app_services: AppServices, bank: Account, cash: Account,
                                        amount: str, field: str) -> None:
    with pytest.raises(ValidationError):
        app_services.account_transfers.create(bank.id, cash.id, amount, fixed_today())
    assert app_services.transactions.list() == []
    assert app_services.account_transfers.list() == []


def test_the_same_account_twice_is_refused(app_services: AppServices, bank: Account) -> None:
    with pytest.raises(ValidationError, match="two different accounts"):
        app_services.account_transfers.create(bank.id, bank.id, "10", fixed_today())


def test_unknown_accounts_are_refused(app_services: AppServices, bank: Account) -> None:
    with pytest.raises(ValidationError, match="does not exist"):
        app_services.account_transfers.create(bank.id, 999, "10", fixed_today())


def test_both_sides_or_neither(app_services: AppServices, bank: Account) -> None:
    """The second side failing (before its account opened) rolls back the first."""
    late = app_services.accounts.create("New card", opening_balance="0",
                                        opening_date=fixed_today())
    with pytest.raises(ValidationError):
        app_services.account_transfers.create(bank.id, late.id, "50",
                                              fixed_today() - timedelta(days=3))
    assert app_services.transactions.list() == []
    assert app_services.balances.balance(bank.id) == Money.of("1000")


def test_one_side_cannot_be_edited_or_deleted_alone(app_services: AppServices, bank: Account,
                                                    cash: Account) -> None:
    transfer = app_services.account_transfers.create(bank.id, cash.id, "300", fixed_today())
    with pytest.raises(ConflictError, match="one side of a transfer"):
        app_services.transactions.delete(transfer.out_transaction_id)
    with pytest.raises(ConflictError, match="one side of a transfer"):
        app_services.transactions.update(transfer.in_transaction_id, TransactionDraft(
            cash.id, TransactionType.ADJUSTMENT_IN, "999", fixed_today()))
    assert app_services.balances.balance(cash.id) == Money.of("300")


def test_deleting_removes_both_sides(app_services: AppServices, bank: Account,
                                     cash: Account) -> None:
    food = app_services.categories.create("Food", CategoryKind.EXPENSE)
    app_services.transactions.create(TransactionDraft(bank.id, TransactionType.EXPENSE, "20",
                                                      fixed_today(), food.id))
    transfer = app_services.account_transfers.create(bank.id, cash.id, "300", fixed_today())
    app_services.account_transfers.delete(transfer.id)
    assert app_services.balances.balance(bank.id) == Money.of("980")
    assert app_services.balances.balance(cash.id) == Money.of("0")
    assert len(app_services.transactions.list()) == 1  # the expense stays
    with pytest.raises(NotFoundError):
        app_services.account_transfers.get(transfer.id)


def test_sides_are_found_by_transaction(app_services: AppServices, bank: Account,
                                        cash: Account) -> None:
    transfer = app_services.account_transfers.create(bank.id, cash.id, "300", fixed_today())
    sides = app_services.account_transfers.by_transaction()
    assert sides == {transfer.out_transaction_id: transfer,
                     transfer.in_transaction_id: transfer}
    assert app_services.account_transfers.for_transaction(transfer.in_transaction_id) == transfer


def test_backups_and_resets_include_transfers(app_services: AppServices, bank: Account,
                                              cash: Account, tmp_path: Path) -> None:
    app_services.account_transfers.create(bank.id, cash.id, "300", fixed_today())
    path = tmp_path / "backup.json"
    app_services.data.export_backup(path)
    app_services.data.reset(RESET_CONFIRMATION)
    assert app_services.account_transfers.list() == []
    app_services.data.import_backup(path)
    [restored] = app_services.account_transfers.list()
    assert restored.amount == Money.of("300")
    assert app_services.balances.balance(cash.id) == Money.of("300")
