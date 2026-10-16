"""Randomised check of the allocation invariants over long operation sequences.

After every operation, successful or rejected:
* Available + Σ allocation balances == real total balance
* the real total balance only changes through transactions
* no allocation balance is negative
"""

import random
from datetime import date

import pytest

from money_manager.core.errors import InsufficientFundsError, ValidationError
from money_manager.domain.entities import Account, Allocation, Category, TransactionDraft
from money_manager.domain.enums import TransactionType
from money_manager.domain.money import Money, sum_money
from money_manager.services import (
    AccountService,
    AllocationService,
    AllocationTransferService,
    BalanceService,
    TransactionService,
)
from tests.services.support import OPENING_DATE, TODAY


def _random_amount(rng: random.Random) -> str:
    centimes = rng.randint(1, 300_000)
    return f"{centimes // 100}.{centimes % 100:02d}"


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_invariants_hold_for_random_operations(
    seed: int,
    accounts: AccountService,
    allocations: AllocationService,
    transfers: AllocationTransferService,
    transactions: TransactionService,
    balances: BalanceService,
    salary: Category,
    food: Category,
) -> None:
    rng = random.Random(seed)
    bank: Account = accounts.create("Bank", opening_balance="5000", opening_date=OPENING_DATE)
    pots: list[Allocation] = [allocations.create(name) for name in ("A", "B", "C")]
    endpoints: list[Allocation | None] = [None, *pots]
    created: list[int] = []

    for _ in range(150):
        total_before = balances.total_balance()
        operation = rng.choice(["transfer", "transfer", "expense", "income", "delete", "undo"])
        changes_real_balance = operation in {"expense", "income", "delete"}
        try:
            if operation == "transfer":
                source, destination = rng.sample(endpoints, 2)
                transfers.transfer(
                    from_allocation_id=None if source is None else source.id,
                    to_allocation_id=None if destination is None else destination.id,
                    amount=_random_amount(rng),
                )
            elif operation in {"expense", "income"}:
                is_income = operation == "income"
                tag = rng.choice(endpoints)
                tx = transactions.create(
                    TransactionDraft(
                        bank.id,
                        TransactionType.INCOME if is_income else TransactionType.EXPENSE,
                        _random_amount(rng),
                        date.fromordinal(rng.randint(OPENING_DATE.toordinal(), TODAY.toordinal())),
                        (salary if is_income else food).id,
                        allocation_id=None if tag is None else tag.id,
                    )
                )
                created.append(tx.id)
            elif operation == "delete" and created:
                transactions.delete(created.pop(rng.randrange(len(created))))
            elif operation == "undo":
                history = transfers.list()
                if history:
                    transfers.undo(rng.choice(history).id)
        except (InsufficientFundsError, ValidationError):
            pass  # rejected operations must leave everything unchanged

        summary = allocations.summary()
        assert summary.total_balance == balances.total_balance()
        assert summary.available + sum_money(r.balance for r in summary.allocations) == (
            summary.total_balance
        )
        assert all(not row.balance.is_negative() for row in summary.allocations)
        if not changes_real_balance:
            assert summary.total_balance == total_before

    report = allocations.check_consistency()
    assert {issue.code for issue in report.issues} <= {"over_allocated"}
    assert report.summary.total_balance == balances.total_balance()
    assert isinstance(report.summary.available, Money)
