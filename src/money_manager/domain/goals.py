"""Financial goals: progress, deadlines and pace (pure, deterministic).

Rules
-----
* Progress = current ÷ target, exact ``Decimal`` rounded half-up to four
  places. It may exceed 1 (over-funded); only the progress *bar* is capped.
* Current amount of an allocation-backed goal = that allocation's balance,
  derived every time and never stored. A manual goal's current amount is a
  user-entered number that is not part of any balance or allocation.
* A goal is complete when current ≥ target.
* With a deadline: overdue when the deadline has passed without completion;
  otherwise on track when current ≥ the linear expectation between the start
  date and the deadline, else behind.
* Required per month = remaining ÷ months left (average Gregorian month of
  30.436875 days), rounded half-up to the centime; everything remaining is
  needed now when the deadline is today.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from money_manager.domain.health import RATIO_QUANTUM
from money_manager.domain.money import Money, sum_money

DAYS_PER_MONTH = Decimal("30.436875")  # 365.2425 / 12
_CENT = Decimal("0.01")


class GoalStatus(StrEnum):
    COMPLETED = "completed"
    OVERDUE = "overdue"
    ON_TRACK = "on_track"
    BEHIND = "behind"
    IN_PROGRESS = "in_progress"  # no deadline to measure pace against


@dataclass(frozen=True, slots=True)
class Goal:
    id: int
    name: str
    description: str
    target: Money
    start_date: date
    deadline: date | None
    allocation_id: int | None  # money kept in this allocation
    manual_amount: Money | None  # set only for manually tracked goals

    @property
    def is_manual(self) -> bool:
        return self.allocation_id is None


@dataclass(frozen=True, slots=True)
class GoalProgress:
    goal: Goal
    current: Money
    today: date
    allocation_name: str | None = None

    @property
    def progress(self) -> Decimal:
        """current ÷ target (0 when nothing is saved); may exceed 1."""
        current = max(self.current.amount, Decimal(0))
        return (current / self.goal.target.amount).quantize(RATIO_QUANTUM, rounding=ROUND_HALF_UP)

    @property
    def bar_fraction(self) -> Decimal:
        return min(self.progress, Decimal(1))

    @property
    def saved(self) -> Money:
        """The current amount, never below zero (consistent with ``progress``)."""
        return self.current if self.current.is_positive() else Money.zero(self.current.currency)

    @property
    def remaining(self) -> Money:
        gap = self.goal.target - self.saved
        return gap if gap.is_positive() else Money.zero(gap.currency)

    @property
    def is_complete(self) -> bool:
        return self.current >= self.goal.target

    @property
    def days_left(self) -> int | None:
        if self.goal.deadline is None:
            return None
        return (self.goal.deadline - self.today).days

    @property
    def expected_now(self) -> Money | None:
        """Where a steady saver would be today (linear from start date to deadline)."""
        deadline = self.goal.deadline
        if deadline is None:
            return None
        total_days = (deadline - self.goal.start_date).days
        if total_days <= 0 or self.today >= deadline:
            return self.goal.target
        elapsed = max((self.today - self.goal.start_date).days, 0)
        expected = self.goal.target.amount * elapsed / total_days
        return Money(expected.quantize(_CENT, rounding=ROUND_HALF_UP), self.goal.target.currency)

    @property
    def status(self) -> GoalStatus:
        if self.is_complete:
            return GoalStatus.COMPLETED
        expected = self.expected_now
        if expected is None:
            return GoalStatus.IN_PROGRESS
        days_left = self.days_left
        assert days_left is not None
        if days_left < 0:
            return GoalStatus.OVERDUE
        return GoalStatus.ON_TRACK if self.current >= expected else GoalStatus.BEHIND

    @property
    def required_per_month(self) -> Money | None:
        """Saving needed per month to reach the target by the deadline."""
        days_left = self.days_left
        if days_left is None or days_left < 0 or self.is_complete:
            return None
        remaining = self.remaining.amount
        if days_left == 0:
            return self.remaining
        months_left = Decimal(days_left) / DAYS_PER_MONTH
        per_month = remaining / max(months_left, Decimal(1))
        return Money(per_month.quantize(_CENT, rounding=ROUND_HALF_UP), self.goal.target.currency)


@dataclass(frozen=True, slots=True)
class GoalsSummary:
    goals: tuple[GoalProgress, ...]
    currency: str

    @property
    def active(self) -> tuple[GoalProgress, ...]:
        return tuple(g for g in self.goals if not g.is_complete)

    @property
    def completed_count(self) -> int:
        return sum(1 for g in self.goals if g.is_complete)

    @property
    def total_target(self) -> Money:
        return sum_money((g.goal.target for g in self.goals), self.currency)

    @property
    def total_saved(self) -> Money:
        """Money counted towards goals, each goal capped at its own target."""
        return sum_money((min(g.saved, g.goal.target) for g in self.goals), self.currency)

    @property
    def overall_progress(self) -> Decimal | None:
        target = self.total_target
        if not target.is_positive():
            return None
        return (self.total_saved.amount / target.amount).quantize(
            RATIO_QUANTUM, rounding=ROUND_HALF_UP
        )

    @property
    def required_per_month(self) -> Money:
        return sum_money(
            (g.required_per_month for g in self.goals if g.required_per_month is not None),
            self.currency,
        )

    def count(self, status: GoalStatus) -> int:
        return sum(1 for g in self.goals if g.status is status)


def order_goals(goals: Sequence[GoalProgress]) -> tuple[GoalProgress, ...]:
    """Unfinished goals first (nearest deadline first, undated last), then completed ones."""
    def key(item: GoalProgress) -> tuple[int, date, str]:
        deadline = item.goal.deadline or date.max
        return (1 if item.is_complete else 0, deadline, item.goal.name.casefold())

    return tuple(sorted(goals, key=key))
