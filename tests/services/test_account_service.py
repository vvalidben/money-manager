from datetime import date

import pytest

from money_manager.core.errors import ConflictError, NotFoundError, ValidationError
from money_manager.domain.entities import Account, Category
from money_manager.domain.enums import TransactionType
from money_manager.domain.money import Money
from money_manager.services import AccountService, BalanceService
from tests.services.support import OPENING_DATE, TODAY, AddTransaction


def test_create_with_opening_balance(accounts: AccountService, balances: BalanceService) -> None:
    account = accounts.create("Bank", opening_balance="30000.00", opening_date=OPENING_DATE)

    assert account.opening_balance == Money.of("30000")
    assert account.currency == "MAD"
    assert balances.balance(account.id) == Money.of("30000")


def test_defaults(accounts: AccountService) -> None:
    account = accounts.create("Wallet")

    assert account.opening_balance == Money.zero()
    assert account.opening_date == TODAY


def test_negative_opening_balance_is_allowed(accounts: AccountService) -> None:
    assert accounts.create("Card", opening_balance="-500.75").opening_balance == Money.of("-500.75")


def test_get_and_list(accounts: AccountService) -> None:
    bank = accounts.create("bank")
    cash = accounts.create("Cash")

    assert accounts.get(bank.id) == bank
    assert [a.name for a in accounts.list()] == ["bank", "Cash"]
    assert cash in accounts.list()


def test_duplicate_names_are_case_insensitive(accounts: AccountService) -> None:
    accounts.create("Bank")

    with pytest.raises(ConflictError):
        accounts.create("  BANK ")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"name": ""},
        {"name": "Bank", "opening_balance": 100.5},
        {"name": "Bank", "opening_balance": "1.999"},
        {"name": "Bank", "opening_date": date(2026, 6, 16)},
        {"name": "Bank", "currency": "dirham"},
    ],
)
def test_invalid_input(accounts: AccountService, kwargs: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        accounts.create(**kwargs)  # type: ignore[arg-type]
    assert accounts.list() == []


def test_update_recalculates_balance(
    accounts: AccountService, balances: BalanceService, account: Account, food: Category,
    add: AddTransaction,
) -> None:
    add(TransactionType.EXPENSE, "100", food)

    updated = accounts.update(
        account.id, name="Main account", opening_balance="1000", opening_date=OPENING_DATE
    )

    assert updated.name == "Main account"
    assert balances.balance(account.id) == Money.of("900")


def test_update_rejects_name_of_other_account(accounts: AccountService, account: Account) -> None:
    accounts.create("Savings")

    with pytest.raises(ConflictError):
        accounts.update(account.id, name="savings", opening_balance="0", opening_date=OPENING_DATE)


def test_update_can_keep_own_name(accounts: AccountService, account: Account) -> None:
    updated = accounts.update(account.id, name="MAIN", opening_balance="5", opening_date=OPENING_DATE)

    assert updated.name == "MAIN"


def test_opening_date_cannot_move_past_first_transaction(
    accounts: AccountService, account: Account, food: Category, add: AddTransaction
) -> None:
    add(TransactionType.EXPENSE, "10", food, on=date(2026, 3, 1))

    with pytest.raises(ValidationError, match="first transaction"):
        accounts.update(account.id, name="Main", opening_balance="0", opening_date=date(2026, 3, 2))
    accounts.update(account.id, name="Main", opening_balance="0", opening_date=date(2026, 3, 1))


def test_delete_empty_account(accounts: AccountService, account: Account) -> None:
    accounts.delete(account.id)

    with pytest.raises(NotFoundError):
        accounts.get(account.id)


def test_cannot_delete_account_with_transactions(
    accounts: AccountService, account: Account, salary: Category, add: AddTransaction
) -> None:
    add(TransactionType.INCOME, "1", salary)

    with pytest.raises(ConflictError):
        accounts.delete(account.id)
    assert accounts.get(account.id) == account


@pytest.mark.parametrize("missing_id", [999, "1", None])
def test_unknown_account(accounts: AccountService, missing_id: object) -> None:
    with pytest.raises(NotFoundError):
        accounts.get(missing_id)  # type: ignore[arg-type]
    with pytest.raises(NotFoundError):
        accounts.delete(missing_id)  # type: ignore[arg-type]
