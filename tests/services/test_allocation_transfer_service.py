from datetime import date

import pytest

from money_manager.core.errors import (
    ConflictError,
    InsufficientFundsError,
    NotFoundError,
    ValidationError,
)
from money_manager.domain.entities import Account, Allocation, Category, TransactionDraft
from money_manager.domain.enums import TransactionType
from money_manager.domain.money import Money
from money_manager.services import (
    AccountService,
    AllocationService,
    AllocationTransferService,
    BalanceService,
    TransactionService,
)
from tests.services.support import OPENING_DATE, TODAY


@pytest.fixture
def bank(accounts: AccountService) -> Account:
    return accounts.create("Bank", opening_balance="10000", opening_date=OPENING_DATE)


@pytest.fixture
def savings(allocations: AllocationService, bank: Account) -> Allocation:
    return allocations.create("Savings", initial_amount="3000")


@pytest.fixture
def investments(allocations: AllocationService, bank: Account) -> Allocation:
    return allocations.create("Investments", initial_amount="2000")


def _state(allocations: AllocationService, *items: Allocation) -> tuple[Money, ...]:
    summary = allocations.summary()
    return (summary.total_balance, *(summary.balance_of(a.id) for a in items), summary.available)


def test_requirements_example(
    allocations: AllocationService,
    transfers: AllocationTransferService,
    transactions: TransactionService,
    balances: BalanceService,
    bank: Account,
    savings: Allocation,
    investments: Allocation,
    food: Category,
) -> None:
    # Starting: balance 10,000 = Savings 3,000 + Investments 2,000 + Available 5,000
    assert _state(allocations, savings, investments) == (
        Money.of("10000"), Money.of("3000"), Money.of("2000"), Money.of("5000"),
    )

    # Move 500 from Available to Investments: the total must not change.
    transfers.transfer(from_allocation_id=None, to_allocation_id=investments.id, amount="500")
    assert _state(allocations, savings, investments) == (
        Money.of("10000"), Money.of("3000"), Money.of("2500"), Money.of("4500"),
    )
    assert balances.total_balance() == Money.of("10000")

    # A real expense of 1,000 (not tagged to an allocation) is paid from Available.
    transactions.create(
        TransactionDraft(bank.id, TransactionType.EXPENSE, "1000", TODAY, food.id)
    )
    assert balances.total_balance() == Money.of("9000")
    assert _state(allocations, savings, investments) == (
        Money.of("9000"), Money.of("3000"), Money.of("2500"), Money.of("3500"),
    )
    assert allocations.check_consistency().is_consistent


def test_transfer_between_allocations(
    allocations: AllocationService, transfers: AllocationTransferService,
    savings: Allocation, investments: Allocation,
) -> None:
    transfers.transfer(from_allocation_id=savings.id, to_allocation_id=investments.id, amount="750.25")

    assert _state(allocations, savings, investments) == (
        Money.of("10000"), Money.of("2249.75"), Money.of("2750.25"), Money.of("5000"),
    )


def test_transfer_back_to_available(
    allocations: AllocationService, transfers: AllocationTransferService, savings: Allocation
) -> None:
    transfers.transfer(from_allocation_id=savings.id, to_allocation_id=None, amount="3000")

    assert allocations.balance(savings.id) == Money.zero()
    assert allocations.available() == Money.of("10000")


def test_cannot_allocate_more_than_available(
    allocations: AllocationService, transfers: AllocationTransferService,
    savings: Allocation, investments: Allocation,
) -> None:
    with pytest.raises(InsufficientFundsError, match="Available"):
        transfers.transfer(from_allocation_id=None, to_allocation_id=savings.id, amount="5000.01")

    transfers.transfer(from_allocation_id=None, to_allocation_id=savings.id, amount="5000")
    assert allocations.available() == Money.zero()


def test_cannot_overdraw_an_allocation(
    allocations: AllocationService, transfers: AllocationTransferService,
    savings: Allocation, investments: Allocation,
) -> None:
    before = allocations.summary()

    with pytest.raises(InsufficientFundsError, match="Savings"):
        transfers.transfer(
            from_allocation_id=savings.id, to_allocation_id=investments.id, amount="3000.01"
        )

    assert allocations.summary() == before


@pytest.mark.parametrize(
    ("source", "destination", "amount", "field"),
    [
        (None, None, "1", "to_allocation_id"),
        ("savings", "savings", "1", "to_allocation_id"),
        (None, 999, "1", "to_allocation_id"),
        (999, None, "1", "from_allocation_id"),
        (None, "savings", "0", "amount"),
        (None, "savings", "-10", "amount"),
        (None, "savings", 10.5, "amount"),
        (None, "savings", "1.001", "amount"),
    ],
)
def test_invalid_transfers(
    allocations: AllocationService, transfers: AllocationTransferService, savings: Allocation,
    source: object, destination: object, amount: object, field: str,
) -> None:
    def resolve(value: object) -> object:
        return savings.id if value == "savings" else value

    with pytest.raises(ValidationError) as info:
        transfers.transfer(
            from_allocation_id=resolve(source),  # type: ignore[arg-type]
            to_allocation_id=resolve(destination),  # type: ignore[arg-type]
            amount=amount,  # type: ignore[arg-type]
        )

    assert info.value.field == field
    assert len(transfers.list()) == 1  # only the initial funding


def test_transfer_to_archived_allocation(
    allocations: AllocationService, transfers: AllocationTransferService, savings: Allocation
) -> None:
    allocations.archive(savings.id)

    with pytest.raises(ValidationError, match="archived"):
        transfers.transfer(from_allocation_id=None, to_allocation_id=savings.id, amount="1")


def test_future_or_past_dates(
    transfers: AllocationTransferService, savings: Allocation
) -> None:
    with pytest.raises(ValidationError, match="future"):
        transfers.transfer(
            from_allocation_id=None, to_allocation_id=savings.id, amount="1", on=date(2026, 6, 16)
        )
    past = transfers.transfer(
        from_allocation_id=None, to_allocation_id=savings.id, amount="1", on=date(2026, 2, 1),
        note="catch-up",
    )
    assert (past.occurred_on, past.note) == (date(2026, 2, 1), "catch-up")


def test_list_and_get(
    transfers: AllocationTransferService, savings: Allocation, investments: Allocation
) -> None:
    moved = transfers.transfer(
        from_allocation_id=savings.id, to_allocation_id=investments.id, amount="5"
    )

    assert transfers.get(moved.id) == moved
    assert moved in transfers.list(investments.id)
    assert len(transfers.list(savings.id)) == 2  # funding + move
    assert len(transfers.list()) == 3
    with pytest.raises(NotFoundError):
        transfers.get(999)


class TestUndo:
    def test_undo_restores_previous_state(
        self, allocations: AllocationService, transfers: AllocationTransferService,
        savings: Allocation, investments: Allocation,
    ) -> None:
        before = allocations.summary()
        moved = transfers.transfer(
            from_allocation_id=savings.id, to_allocation_id=investments.id, amount="1000"
        )

        transfers.undo(moved.id)

        assert allocations.summary() == before
        with pytest.raises(NotFoundError):
            transfers.get(moved.id)

    def test_cannot_undo_if_destination_spent_the_money(
        self, allocations: AllocationService, transfers: AllocationTransferService,
        savings: Allocation, investments: Allocation,
    ) -> None:
        moved = transfers.transfer(
            from_allocation_id=savings.id, to_allocation_id=investments.id, amount="1000"
        )
        transfers.transfer(from_allocation_id=investments.id, to_allocation_id=None, amount="2500")

        with pytest.raises(InsufficientFundsError):
            transfers.undo(moved.id)

    def test_cannot_undo_into_archived_allocation(
        self, allocations: AllocationService, transfers: AllocationTransferService,
        savings: Allocation, investments: Allocation,
    ) -> None:
        moved = transfers.transfer(
            from_allocation_id=savings.id, to_allocation_id=investments.id, amount="10"
        )
        allocations.archive(savings.id)

        with pytest.raises(ConflictError, match="archived"):
            transfers.undo(moved.id)

    def test_undo_funding_requires_money_in_allocation(
        self, allocations: AllocationService, transfers: AllocationTransferService,
        savings: Allocation,
    ) -> None:
        [funding] = transfers.list(savings.id)
        transfers.transfer(from_allocation_id=savings.id, to_allocation_id=None, amount="1")

        with pytest.raises(InsufficientFundsError):
            transfers.undo(funding.id)
