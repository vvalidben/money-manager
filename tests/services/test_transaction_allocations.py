"""How real transactions interact with allocations."""

from dataclasses import replace

import pytest

from money_manager.core.errors import InsufficientFundsError, ValidationError
from money_manager.domain.entities import (
    Account,
    Allocation,
    Category,
    TransactionDraft,
    TransactionFilter,
)
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.money import Money
from money_manager.services import (
    AccountService,
    AllocationService,
    AllocationTransferService,
    BalanceService,
    CategoryService,
    TransactionService,
)
from tests.services.support import OPENING_DATE, TODAY


@pytest.fixture
def bank(accounts: AccountService) -> Account:
    return accounts.create("Bank", opening_balance="10000", opening_date=OPENING_DATE)


@pytest.fixture
def bills_category(categories: CategoryService) -> Category:
    return categories.create("Electricity", CategoryKind.EXPENSE)


@pytest.fixture
def bills(allocations: AllocationService, bank: Account) -> Allocation:
    return allocations.create("Bills", initial_amount="3000")


def _expense(bank: Account, category: Category, amount: str, allocation: Allocation | None):
    return TransactionDraft(
        bank.id, TransactionType.EXPENSE, amount, TODAY, category.id,
        allocation_id=None if allocation is None else allocation.id,
    )


def test_untagged_expense_reduces_available_only(
    allocations: AllocationService, transactions: TransactionService, bank: Account,
    bills: Allocation, bills_category: Category,
) -> None:
    transactions.create(_expense(bank, bills_category, "400", None))

    summary = allocations.summary()
    assert summary.total_balance == Money.of("9600")
    assert summary.balance_of(bills.id) == Money.of("3000")
    assert summary.available == Money.of("6600")


def test_tagged_expense_is_paid_from_the_allocation(
    allocations: AllocationService, transactions: TransactionService, bank: Account,
    bills: Allocation, bills_category: Category,
) -> None:
    tx = transactions.create(_expense(bank, bills_category, "400", bills))

    summary = allocations.summary()
    assert tx.allocation_id == bills.id
    assert summary.total_balance == Money.of("9600")
    assert summary.balance_of(bills.id) == Money.of("2600")
    assert summary.available == Money.of("7000")  # unchanged
    assert transactions.list(TransactionFilter(allocation_id=bills.id)) == [tx]


def test_tagged_income_goes_into_the_allocation(
    allocations: AllocationService, transactions: TransactionService, bank: Account,
    salary: Category,
) -> None:
    savings = allocations.create("Savings")

    transactions.create(
        TransactionDraft(bank.id, TransactionType.INCOME, "1200", TODAY, salary.id,
                         allocation_id=savings.id)
    )

    summary = allocations.summary()
    assert summary.total_balance == Money.of("11200")
    assert summary.balance_of(savings.id) == Money.of("1200")
    assert summary.available == Money.of("10000")


def test_tagged_expense_cannot_overdraw_allocation(
    allocations: AllocationService, transactions: TransactionService, bank: Account,
    bills: Allocation, bills_category: Category,
) -> None:
    with pytest.raises(InsufficientFundsError, match="Bills"):
        transactions.create(_expense(bank, bills_category, "3000.01", bills))

    assert transactions.list() == []
    transactions.create(_expense(bank, bills_category, "3000", bills))
    assert allocations.balance(bills.id) == Money.zero()


def test_adjustments_cannot_target_an_allocation(
    transactions: TransactionService, bank: Account, bills: Allocation
) -> None:
    with pytest.raises(ValidationError, match="Available"):
        transactions.create(
            TransactionDraft(bank.id, TransactionType.ADJUSTMENT_OUT, "5", TODAY,
                             allocation_id=bills.id)
        )


def test_unknown_or_archived_allocation(
    allocations: AllocationService, transactions: TransactionService, bank: Account,
    bills: Allocation, bills_category: Category,
) -> None:
    with pytest.raises(ValidationError, match="does not exist"):
        transactions.create(replace(_expense(bank, bills_category, "1", None), allocation_id=999))

    allocations.archive(bills.id)
    with pytest.raises(ValidationError, match="archived"):
        transactions.create(_expense(bank, bills_category, "1", bills))


def test_reconcile_adjustment_affects_available(
    allocations: AllocationService, balances: BalanceService, bank: Account, bills: Allocation
) -> None:
    balances.reconcile(bank.id, "9500")

    summary = allocations.summary()
    assert summary.balance_of(bills.id) == Money.of("3000")
    assert summary.available == Money.of("6500")


class TestEditsAndDeletes:
    def test_moving_expense_between_available_and_allocation(
        self, allocations: AllocationService, transactions: TransactionService, bank: Account,
        bills: Allocation, bills_category: Category,
    ) -> None:
        tx = transactions.create(_expense(bank, bills_category, "500", None))

        transactions.update(tx.id, _expense(bank, bills_category, "500", bills))
        assert allocations.balance(bills.id) == Money.of("2500")
        assert allocations.available() == Money.of("7000")

        transactions.update(tx.id, _expense(bank, bills_category, "500", None))
        assert allocations.balance(bills.id) == Money.of("3000")
        assert allocations.available() == Money.of("6500")

    def test_increasing_tagged_expense_beyond_allocation_is_rejected(
        self, allocations: AllocationService, transactions: TransactionService, bank: Account,
        bills: Allocation, bills_category: Category,
    ) -> None:
        tx = transactions.create(_expense(bank, bills_category, "2000", bills))

        # 3,000 available in Bills before the transaction, so up to 3,000 is fine.
        transactions.update(tx.id, _expense(bank, bills_category, "3000", bills))
        with pytest.raises(InsufficientFundsError):
            transactions.update(tx.id, _expense(bank, bills_category, "3000.01", bills))
        assert transactions.get(tx.id).amount == Money.of("3000")

    def test_deleting_tagged_expense_refunds_allocation(
        self, allocations: AllocationService, transactions: TransactionService, bank: Account,
        bills: Allocation, bills_category: Category,
    ) -> None:
        tx = transactions.create(_expense(bank, bills_category, "700", bills))

        transactions.delete(tx.id)

        assert allocations.balance(bills.id) == Money.of("3000")

    def test_deleting_spent_tagged_income_is_rejected(
        self, allocations: AllocationService, transactions: TransactionService, bank: Account,
        salary: Category, bills_category: Category,
    ) -> None:
        savings = allocations.create("Savings")
        income = transactions.create(
            TransactionDraft(bank.id, TransactionType.INCOME, "1000", TODAY, salary.id,
                             allocation_id=savings.id)
        )
        transactions.create(_expense(bank, bills_category, "600", savings))

        with pytest.raises(InsufficientFundsError, match="Savings"):
            transactions.delete(income.id)
        assert allocations.balance(savings.id) == Money.of("400")

    def test_retagging_income_away_from_spent_allocation_is_rejected(
        self, allocations: AllocationService, transactions: TransactionService, bank: Account,
        salary: Category, bills_category: Category,
    ) -> None:
        savings = allocations.create("Savings")
        draft = TransactionDraft(bank.id, TransactionType.INCOME, "1000", TODAY, salary.id,
                                 allocation_id=savings.id)
        income = transactions.create(draft)
        transactions.create(_expense(bank, bills_category, "600", savings))

        with pytest.raises(InsufficientFundsError):
            transactions.update(income.id, replace(draft, allocation_id=None))

    def test_editing_keeps_archived_allocation(
        self, allocations: AllocationService, transactions: TransactionService,
        transfers: AllocationTransferService, bank: Account, bills: Allocation,
        bills_category: Category,
    ) -> None:
        tx = transactions.create(_expense(bank, bills_category, "3000", bills))
        allocations.archive(bills.id)  # balance is zero, nothing to release

        updated = transactions.update(
            tx.id, replace(_expense(bank, bills_category, "3000", bills), description="Paid")
        )

        assert updated.description == "Paid"


class TestOverAllocation:
    def test_real_spending_can_exceed_available_and_is_reported(
        self, allocations: AllocationService, transactions: TransactionService,
        transfers: AllocationTransferService, bank: Account, bills: Allocation,
        bills_category: Category,
    ) -> None:
        allocations.create("Savings", initial_amount="7000")  # Available is now 0

        # The money really was spent, so the expense is recorded ...
        transactions.create(_expense(bank, bills_category, "1000", None))

        summary = allocations.summary()
        assert summary.total_balance == Money.of("9000")
        assert summary.available == Money.of("-1000")
        assert summary.is_over_allocated
        # ... but no further allocating is allowed until it is resolved.
        with pytest.raises(InsufficientFundsError):
            transfers.transfer(from_allocation_id=None, to_allocation_id=bills.id, amount="1")

        transfers.transfer(from_allocation_id=bills.id, to_allocation_id=None, amount="1000")
        assert not allocations.summary().is_over_allocated
        assert allocations.check_consistency().is_consistent
