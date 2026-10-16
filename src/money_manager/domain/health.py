"""Basic financial-health metrics and how they are judged.

These are deliberately simple, explainable heuristics computed from exact
Decimal values. Ratios are fractions (0.25 = 25 %), rounded half-up to four
decimal places; ``None`` means there is not enough data to say anything.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from money_manager.domain.money import Money

RATIO_QUANTUM = Decimal("0.0001")
MONTHS_QUANTUM = Decimal("0.1")

# Thresholds (initial heuristics, adjustable in one place).
GOOD_SAVINGS_RATE = Decimal("0.20")
GOOD_RUNWAY_MONTHS = Decimal(6)
FAIR_RUNWAY_MONTHS = Decimal(3)
FAIR_SPENDING_INCREASE = Decimal("0.10")


class HealthLevel(StrEnum):
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    UNKNOWN = "unknown"


def ratio(part: Money, whole: Money) -> Decimal | None:
    """``part / whole`` as a fraction, or None when ``whole`` is zero."""
    if whole.is_zero():
        return None
    return (part.amount / whole.amount).quantize(RATIO_QUANTUM, rounding=ROUND_HALF_UP)


def savings_rate(income: Money, expenses: Money) -> Decimal | None:
    """Share of income not spent: (income − expenses) / income. None without income."""
    if not income.is_positive():
        return None
    return ratio(income - expenses, income)


def relative_change(current: Money, previous: Money) -> Decimal | None:
    """(current − previous) / previous; None when there is no positive baseline."""
    if not previous.is_positive():
        return None
    return ratio(current - previous, previous)


def spending_change(current: Money, previous: Money) -> Decimal | None:
    """Relative change in spending: (current − previous) / previous."""
    return relative_change(current, previous)


def runway_months(balance: Money, average_monthly_expenses: Money | None) -> Decimal | None:
    """How many months of typical spending the balance would cover."""
    if average_monthly_expenses is None or not average_monthly_expenses.is_positive():
        return None
    if not balance.is_positive():
        return Decimal(0)
    return (balance.amount / average_monthly_expenses.amount).quantize(
        MONTHS_QUANTUM, rounding=ROUND_HALF_UP
    )


def assess_savings_rate(rate: Decimal | None) -> HealthLevel:
    if rate is None:
        return HealthLevel.UNKNOWN
    if rate >= GOOD_SAVINGS_RATE:
        return HealthLevel.GOOD
    return HealthLevel.FAIR if rate >= 0 else HealthLevel.POOR


def assess_spending_change(change: Decimal | None) -> HealthLevel:
    if change is None:
        return HealthLevel.UNKNOWN
    if change <= 0:
        return HealthLevel.GOOD
    return HealthLevel.FAIR if change <= FAIR_SPENDING_INCREASE else HealthLevel.POOR


def assess_runway(months: Decimal | None) -> HealthLevel:
    if months is None:
        return HealthLevel.UNKNOWN
    if months >= GOOD_RUNWAY_MONTHS:
        return HealthLevel.GOOD
    return HealthLevel.FAIR if months >= FAIR_RUNWAY_MONTHS else HealthLevel.POOR


@dataclass(frozen=True, slots=True)
class HealthMetrics:
    savings_rate: Decimal | None
    spending_change: Decimal | None
    runway_months: Decimal | None
    allocated_share: Decimal | None

    @property
    def savings_level(self) -> HealthLevel:
        return assess_savings_rate(self.savings_rate)

    @property
    def spending_level(self) -> HealthLevel:
        return assess_spending_change(self.spending_change)

    @property
    def runway_level(self) -> HealthLevel:
        return assess_runway(self.runway_months)
