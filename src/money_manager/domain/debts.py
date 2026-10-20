"""Debts and loans: money lent to someone, or borrowed (pure).

* **Lent** — someone owes you (e.g. a loan to a friend): it adds to your net worth.
* **Borrowed** — you owe it (e.g. a car loan): it is subtracted from your net worth.

A debt starts at its amount on its start date; each repayment lowers what is
outstanding. When money moved through one of your accounts it was recorded as
a balance *adjustment* (like a transfer: neither income nor spending), so the
balance plus the outstanding loans stays your true net worth.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from money_manager.domain.money import Money, sum_money

MAX_DEBT_NAME_LENGTH = 80


class DebtDirection(StrEnum):
    LENT = "lent"  # someone owes you
    BORROWED = "borrowed"  # you owe


@dataclass(frozen=True, slots=True)
class DebtPayment:
    id: int
    debt_id: int
    amount: Money
    paid_on: date
    transaction_id: int | None
    note: str


@dataclass(frozen=True, slots=True)
class Debt:
    id: int
    name: str
    direction: DebtDirection
    amount: Money  # the original amount, always positive
    start_date: date
    due_date: date | None
    notes: str
    payments: tuple[DebtPayment, ...] = ()

    @property
    def repaid(self) -> Money:
        return sum_money((p.amount for p in self.payments), self.amount.currency)

    @property
    def remaining(self) -> Money:
        left = self.amount - self.repaid
        return left if left.is_positive() else Money.zero(self.amount.currency)

    @property
    def is_settled(self) -> bool:
        return self.remaining.is_zero()

    def is_overdue(self, today: date) -> bool:
        return not self.is_settled and self.due_date is not None and self.due_date < today

    def outstanding_on(self, day: date) -> Money:
        """What was still owed at the end of ``day`` (nothing before the start)."""
        if day < self.start_date:
            return Money.zero(self.amount.currency)
        paid = sum_money((p.amount for p in self.payments if p.paid_on <= day),
                         self.amount.currency)
        left = self.amount - paid
        return left if left.is_positive() else Money.zero(self.amount.currency)

    @property
    def sign(self) -> int:
        """+1 when it adds to your net worth (lent), −1 when it lowers it."""
        return 1 if self.direction is DebtDirection.LENT else -1


@dataclass(frozen=True, slots=True)
class DebtSummary:
    owed_to_you: Money
    you_owe: Money

    @property
    def net(self) -> Money:
        """What the loans add to your net worth (negative when you owe more)."""
        return self.owed_to_you - self.you_owe


def debt_summary(debts: Iterable[Debt], currency: str, day: date | None = None) -> DebtSummary:
    """Outstanding totals (on ``day``, or now)."""
    lent, borrowed = [], []
    for debt in debts:
        left = debt.remaining if day is None else debt.outstanding_on(day)
        (lent if debt.direction is DebtDirection.LENT else borrowed).append(left)
    return DebtSummary(sum_money(lent, currency), sum_money(borrowed, currency))
