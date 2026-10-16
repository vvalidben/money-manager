"""The balance formula."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Self

from money_manager.domain.enums import TransactionType
from money_manager.domain.money import Money


@dataclass(frozen=True, slots=True)
class BalanceBreakdown:
    """Components of an account balance.

    balance = opening balance + income − expenses
              + positive adjustments − negative adjustments
    """

    opening_balance: Money
    income: Money
    expenses: Money
    adjustments_in: Money
    adjustments_out: Money

    @property
    def balance(self) -> Money:
        return (
            self.opening_balance
            + self.income
            - self.expenses
            + self.adjustments_in
            - self.adjustments_out
        )

    @classmethod
    def from_totals(
        cls, opening_balance: Money, totals_in_minor_units: Mapping[TransactionType, int]
    ) -> Self:
        """Build from per-type sums of (positive) transaction amounts."""
        currency = opening_balance.currency

        def total(transaction_type: TransactionType) -> Money:
            return Money.from_minor_units(totals_in_minor_units.get(transaction_type, 0), currency)

        return cls(
            opening_balance=opening_balance,
            income=total(TransactionType.INCOME),
            expenses=total(TransactionType.EXPENSE),
            adjustments_in=total(TransactionType.ADJUSTMENT_IN),
            adjustments_out=total(TransactionType.ADJUSTMENT_OUT),
        )
