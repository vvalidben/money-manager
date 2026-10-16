"""How the real balance is organised into allocations.

Rules
-----
* Allocations organise money that already exists; they never add money.
* ``Available`` is not stored anywhere. It is always derived:

      available = total real balance − Σ allocation balances

  so ``available + Σ allocation balances == total real balance`` holds by
  construction and nothing can be counted twice.
* An allocation balance is the sum of transfers into it, minus transfers out
  of it, plus income tagged to it, minus expenses tagged to it.
* Transfers only move money between allocations and Available; they never
  touch the real balance.
* Untagged real transactions (and balance adjustments) change Available.
* Allocation balances may never be negative. Available may become negative
  only through real transactions (money was spent that had been set aside);
  that state is reported as over-allocation and blocks further allocating.
"""

from dataclasses import dataclass

from money_manager.domain.entities import Allocation
from money_manager.domain.money import Money, sum_money

AVAILABLE_LABEL = "Available"


@dataclass(frozen=True, slots=True)
class AllocationBalance:
    allocation: Allocation
    balance: Money


@dataclass(frozen=True, slots=True)
class AllocationSummary:
    total_balance: Money
    allocations: tuple[AllocationBalance, ...]

    @property
    def allocated_total(self) -> Money:
        return sum_money(
            (row.balance for row in self.allocations), self.total_balance.currency
        )

    @property
    def available(self) -> Money:
        return self.total_balance - self.allocated_total

    @property
    def is_over_allocated(self) -> bool:
        return self.available.is_negative()

    @property
    def shortfall(self) -> Money:
        """How much must be returned to Available to stop being over-allocated."""
        available = self.available
        return -available if available.is_negative() else Money.zero(available.currency)

    def balance_of(self, allocation_id: int) -> Money:
        for row in self.allocations:
            if row.allocation.id == allocation_id:
                return row.balance
        return Money.zero(self.total_balance.currency)
