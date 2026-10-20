"""Monthly budgets per expense category (pure, deterministic).

A budget is a monthly limit for one expense category. Its status compares the
category's spending in the current calendar month (expense transactions, month
to date) with the limit:

* **Over** — spending is above the limit.
* **Near limit** — spending has reached 85 % of the limit.
* **On track** — otherwise.

The month-end projection extrapolates the spending so far at its daily pace;
it is only shown once a few days of the month have passed.
"""

import calendar
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from money_manager.domain.money import Money, sum_money
from money_manager.core.i18n import tr

NEAR_LIMIT = Decimal("0.85")
RATIO_QUANTUM = Decimal("0.0001")
MIN_DAYS_FOR_PROJECTION = 3


class BudgetLevel(StrEnum):
    ON_TRACK = "on_track"
    NEAR_LIMIT = "near_limit"
    OVER = "over"

    @property
    def label(self) -> str:
        return {"on_track": tr("On track"), "near_limit": tr("Near limit"), "over": tr("Over")}[self.value]


@dataclass(frozen=True, slots=True)
class Budget:
    id: int
    category_id: int
    limit: Money  # per calendar month, always positive


@dataclass(frozen=True, slots=True)
class BudgetStatus:
    budget: Budget
    category_name: str
    spent: Money  # this month to date
    today: date

    @property
    def remaining(self) -> Money:
        """Left to spend this month; negative when over the limit."""
        return self.budget.limit - self.spent

    @property
    def ratio(self) -> Decimal:
        """spent ÷ limit (may exceed 1)."""
        return (self.spent.amount / self.budget.limit.amount).quantize(
            RATIO_QUANTUM, rounding=ROUND_HALF_UP)

    @property
    def level(self) -> BudgetLevel:
        if self.spent.amount > self.budget.limit.amount:
            return BudgetLevel.OVER
        # Exact comparison: the rounded ratio would call 849.99 of 1,000 "near".
        if self.spent.amount >= self.budget.limit.amount * NEAR_LIMIT:
            return BudgetLevel.NEAR_LIMIT
        return BudgetLevel.ON_TRACK

    @property
    def projected(self) -> Money | None:
        """Month-end spending at the pace so far; None early in the month."""
        days = calendar.monthrange(self.today.year, self.today.month)[1]
        elapsed = self.today.day
        if elapsed < MIN_DAYS_FOR_PROJECTION or elapsed >= days:
            return None
        per_day = self.spent.amount / elapsed
        value = (per_day * days).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return Money(value, self.spent.currency)


@dataclass(frozen=True, slots=True)
class BudgetSummary:
    statuses: tuple[BudgetStatus, ...]  # most used (by ratio) first
    currency: str

    @property
    def planned(self) -> Money:
        return sum_money((s.budget.limit for s in self.statuses), self.currency)

    @property
    def spent(self) -> Money:
        return sum_money((s.spent for s in self.statuses), self.currency)

    @property
    def remaining(self) -> Money:
        return self.planned - self.spent

    @property
    def over_count(self) -> int:
        return sum(1 for s in self.statuses if s.level is BudgetLevel.OVER)
