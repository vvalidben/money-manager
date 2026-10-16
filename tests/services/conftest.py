from datetime import date

import pytest

from money_manager.domain.entities import Account, Category, Transaction, TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.persistence.database import Database
from money_manager.services import (
    AccountService,
    AllocationService,
    AllocationTransferService,
    BalanceService,
    CategoryService,
    TransactionService,
)
from tests.services.support import OPENING_DATE, TODAY, AddTransaction, fixed_today


@pytest.fixture
def accounts(database: Database) -> AccountService:
    return AccountService(database, today=fixed_today)


@pytest.fixture
def categories(database: Database) -> CategoryService:
    return CategoryService(database)


@pytest.fixture
def transactions(database: Database) -> TransactionService:
    return TransactionService(database, today=fixed_today)


@pytest.fixture
def balances(database: Database, transactions: TransactionService) -> BalanceService:
    return BalanceService(database, transactions, today=fixed_today)


@pytest.fixture
def allocations(database: Database, balances: BalanceService) -> AllocationService:
    return AllocationService(database, balances, today=fixed_today)


@pytest.fixture
def transfers(database: Database) -> AllocationTransferService:
    return AllocationTransferService(database, today=fixed_today)


@pytest.fixture
def account(accounts: AccountService) -> Account:
    return accounts.create("Main", opening_balance="0", opening_date=OPENING_DATE)


@pytest.fixture
def salary(categories: CategoryService) -> Category:
    return categories.create("Salary", CategoryKind.INCOME)


@pytest.fixture
def food(categories: CategoryService) -> Category:
    return categories.create("Food", CategoryKind.EXPENSE)


@pytest.fixture
def add(transactions: TransactionService, account: Account) -> AddTransaction:
    """Shortcut: add(type, amount, category=None, on=TODAY, account_id=None, **extra)."""

    def _add(
        transaction_type: TransactionType | str,
        amount: object,
        category: Category | None = None,
        on: date = TODAY,
        account_id: int | None = None,
        **extra: object,
    ) -> Transaction:
        return transactions.create(
            TransactionDraft(
                account_id=account.id if account_id is None else account_id,
                type=transaction_type,
                amount=amount,  # type: ignore[arg-type]
                occurred_on=on,
                category_id=None if category is None else category.id,
                **extra,  # type: ignore[arg-type]
            )
        )

    return _add
