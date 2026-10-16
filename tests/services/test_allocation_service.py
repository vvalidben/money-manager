import pytest

from money_manager.core.errors import (
    ConflictError,
    InsufficientFundsError,
    NotFoundError,
    ValidationError,
)
from money_manager.domain.entities import Account, Category
from money_manager.domain.enums import TransactionType
from money_manager.domain.money import Money
from money_manager.services import (
    AccountService,
    AllocationService,
    AllocationTransferService,
    BalanceService,
)
from tests.services.support import OPENING_DATE, AddTransaction

USER_ALLOCATIONS = [
    "Savings", "Investments", "Bills", "Subscriptions", "Emergency Fund", "Travel", "Gaming",
    "Education", "Wedding 2027",
]


@pytest.fixture
def funded(accounts: AccountService) -> Account:
    return accounts.create("Bank", opening_balance="10000", opening_date=OPENING_DATE)


def test_fresh_database_has_no_allocations(allocations: AllocationService) -> None:
    assert allocations.list(include_archived=True) == []


def test_everything_is_available_without_allocations(
    allocations: AllocationService, funded: Account
) -> None:
    summary = allocations.summary()

    assert summary.total_balance == Money.of("10000")
    assert summary.allocations == ()
    assert summary.available == Money.of("10000")


def test_user_defined_names(allocations: AllocationService, funded: Account) -> None:
    for name in USER_ALLOCATIONS:
        allocations.create(name)

    assert sorted(a.name for a in allocations.list()) == sorted(USER_ALLOCATIONS)
    assert allocations.available() == Money.of("10000")


def test_create_with_initial_amount_comes_from_available(
    allocations: AllocationService, transfers: AllocationTransferService, funded: Account
) -> None:
    savings = allocations.create("Savings", initial_amount="3000")

    assert allocations.balance(savings.id) == Money.of("3000")
    assert allocations.available() == Money.of("7000")
    assert allocations.summary().total_balance == Money.of("10000")
    [transfer] = transfers.list()
    assert (transfer.from_allocation_id, transfer.to_allocation_id) == (None, savings.id)


def test_initial_amount_cannot_exceed_available(
    allocations: AllocationService, funded: Account
) -> None:
    with pytest.raises(InsufficientFundsError):
        allocations.create("Savings", initial_amount="10000.01")

    assert allocations.list() == []  # the allocation itself was rolled back too


def test_initial_amount_may_use_everything(allocations: AllocationService, funded: Account) -> None:
    allocations.create("Savings", initial_amount="10000")

    assert allocations.available() == Money.zero()


@pytest.mark.parametrize("amount", ["-1", 1.5, "0.001"])
def test_invalid_initial_amount(
    allocations: AllocationService, funded: Account, amount: object
) -> None:
    with pytest.raises(ValidationError):
        allocations.create("Savings", initial_amount=amount)  # type: ignore[arg-type]


def test_duplicate_and_reserved_names(allocations: AllocationService) -> None:
    allocations.create("Savings")

    with pytest.raises(ConflictError):
        allocations.create("  SAVINGS ")
    with pytest.raises(ValidationError):
        allocations.create("Available")


def test_rename(allocations: AllocationService, funded: Account) -> None:
    savings = allocations.create("Savings", initial_amount="100")
    allocations.create("Travel")

    assert allocations.rename(savings.id, "Rainy day").name == "Rainy day"
    assert allocations.balance(savings.id) == Money.of("100")
    with pytest.raises(ConflictError):
        allocations.rename(savings.id, "travel")
    with pytest.raises(ValidationError):
        allocations.rename(savings.id, "Unallocated")


def test_archive_returns_money_to_available(
    allocations: AllocationService, funded: Account
) -> None:
    travel = allocations.create("Travel", initial_amount="1500")

    archived = allocations.archive(travel.id)

    assert archived.is_archived
    assert allocations.balance(travel.id) == Money.zero()
    assert allocations.available() == Money.of("10000")
    assert allocations.list() == []
    assert allocations.list(include_archived=True) == [archived]
    assert allocations.check_consistency().is_consistent


def test_archive_is_idempotent_and_restorable(
    allocations: AllocationService, funded: Account
) -> None:
    travel = allocations.create("Travel", initial_amount="100")
    allocations.archive(travel.id)
    allocations.archive(travel.id)

    restored = allocations.restore(travel.id)

    assert not restored.is_archived
    assert allocations.balance(travel.id) == Money.zero()


def test_delete_unused(allocations: AllocationService) -> None:
    gaming = allocations.create("Gaming")

    allocations.delete(gaming.id)

    with pytest.raises(NotFoundError):
        allocations.get(gaming.id)


def test_cannot_delete_used_allocation(allocations: AllocationService, funded: Account) -> None:
    gaming = allocations.create("Gaming", initial_amount="1")

    with pytest.raises(ConflictError, match="archive"):
        allocations.delete(gaming.id)


def test_unknown_allocation(allocations: AllocationService) -> None:
    for call in (allocations.get, allocations.balance, allocations.archive, allocations.delete):
        with pytest.raises(NotFoundError):
            call(404)


class TestConsistency:
    def test_clean_state(
        self, allocations: AllocationService, funded: Account, food: Category,
        add: AddTransaction,
    ) -> None:
        allocations.create("Savings", initial_amount="3000")
        add(TransactionType.EXPENSE, "1000", food, account_id=funded.id)

        report = allocations.check_consistency()

        assert report.is_consistent
        assert report.summary.available == Money.of("6000")

    def test_ledger_total_matches_balance_service(
        self, allocations: AllocationService, balances: BalanceService, accounts: AccountService,
        salary: Category, food: Category, add: AddTransaction,
    ) -> None:
        bank = accounts.create("Bank", opening_balance="1000.55", opening_date=OPENING_DATE)
        cash = accounts.create("Cash", opening_balance="-20.10", opening_date=OPENING_DATE)
        add(TransactionType.INCOME, "300.33", salary, account_id=bank.id)
        add(TransactionType.EXPENSE, "12.01", food, account_id=cash.id)
        add(TransactionType.ADJUSTMENT_OUT, "0.07", account_id=cash.id)

        assert allocations.summary().total_balance == balances.total_balance()

    def test_reports_over_allocation(
        self, allocations: AllocationService, funded: Account, food: Category,
        add: AddTransaction,
    ) -> None:
        allocations.create("Savings", initial_amount="9000")
        add(TransactionType.EXPENSE, "1500", food, account_id=funded.id)

        report = allocations.check_consistency()

        assert [issue.code for issue in report.issues] == ["over_allocated"]
        assert report.summary.shortfall == Money.of("500")

    def test_detects_corrupted_data(
        self, allocations: AllocationService, funded: Account, database
    ) -> None:
        savings = allocations.create("Savings", initial_amount="100")
        with database.engine.begin() as conn:  # bypass the services on purpose
            conn.exec_driver_sql(
                "INSERT INTO allocation_transfers (from_allocation_id, to_allocation_id, "
                "amount_minor, occurred_on, note) VALUES (?, NULL, 50000, '2026-06-01', '')",
                (savings.id,),
            )

        codes = {issue.code for issue in allocations.check_consistency().issues}

        assert "negative_allocation" in codes
