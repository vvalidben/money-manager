"""Cash-flow forecast: where the balance is heading (pure, deterministic).

The forecast starts from today's total balance and adds, day by day:

* **Scheduled events** — every date of the active recurring entries and
  subscriptions in the horizon, and the loans due in it (what is left to repay:
  money coming back when you lent it, going out when you borrowed it). Dates
  already due but not recorded yet count today.
* **Usual income and spending** — the average of the last complete months
  (up to three), *minus* the monthly cost of the recurring entries and
  subscriptions, since those are already scheduled events. It is spread evenly
  over the days (a year of 365 days).

It is an estimate from your own records, not a promise: the line shows where the
balance goes if the coming months look like the last ones.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from money_manager.domain.money import Money
from money_manager.domain.periods import month_start, shift_months

FORECAST_MONTHS = 6
HISTORY_MONTHS = 3
_CENT = Decimal("0.01")
_DAYS_PER_MONTH = Decimal(365) / Decimal(12)


class EventKind(StrEnum):
    RECURRING = "recurring"
    SUBSCRIPTION = "subscription"
    LOAN = "loan"


@dataclass(frozen=True, slots=True)
class ForecastEvent:
    day: date
    label: str
    amount: Money  # signed: positive comes in, negative goes out
    kind: EventKind


@dataclass(frozen=True, slots=True)
class ForecastPoint:
    day: date
    balance: Money


@dataclass(frozen=True, slots=True)
class Forecast:
    start: date  # today
    end: date
    opening: Money  # today's total balance
    points: tuple[ForecastPoint, ...]  # one per day, from today to ``end``
    events: tuple[ForecastEvent, ...]  # by date
    usual_income: Money  # per month, beyond the scheduled events
    usual_spending: Money  # per month, beyond the scheduled events
    history_months: int  # complete months the usual figures come from (0: none yet)

    @property
    def closing(self) -> Money:
        return self.points[-1].balance

    @property
    def lowest(self) -> ForecastPoint:
        """The lowest projected balance (the earliest day when several are equal)."""
        return min(self.points, key=lambda p: (p.balance.amount, p.day))

    @property
    def first_below_zero(self) -> ForecastPoint | None:
        return next((p for p in self.points if p.balance.is_negative()), None)

    @property
    def tight_months(self) -> tuple[date, ...]:
        """Months (first days) in which the projected balance goes below zero."""
        months: list[date] = []
        for point in self.points:
            month = month_start(point.day)
            if point.balance.is_negative() and month not in months:
                months.append(month)
        return tuple(months)

    def balance_after(self, event: ForecastEvent) -> Money:
        return next(p.balance for p in self.points if p.day == event.day)


def monthly_equivalent(amount: Money, payments_per_year: int) -> Money:
    value = (amount.amount * payments_per_year / 12).quantize(_CENT, rounding=ROUND_HALF_UP)
    return Money(value, amount.currency)


def build_forecast(today: date, opening: Money, events: Iterable[ForecastEvent], *,
                   usual_income: Money, usual_spending: Money, history_months: int,
                   months: int = FORECAST_MONTHS) -> Forecast:
    end = max(shift_months(today, months) - timedelta(days=1), today)
    scheduled = sorted((e for e in events if e.day <= end),
                       key=lambda e: (max(e.day, today), e.kind.value, e.label.casefold()))
    placed = tuple(ForecastEvent(max(e.day, today), e.label, e.amount, e.kind)
                   for e in scheduled)
    by_day: dict[date, Decimal] = {}
    for event in placed:
        by_day[event.day] = by_day.get(event.day, Decimal(0)) + event.amount.amount
    daily_usual = (usual_income.amount - usual_spending.amount) / _DAYS_PER_MONTH
    points: list[ForecastPoint] = []
    scheduled_total = Decimal(0)
    day = today
    elapsed = 0
    while day <= end:
        scheduled_total += by_day.get(day, Decimal(0))
        usual = (daily_usual * elapsed).quantize(_CENT, rounding=ROUND_HALF_UP)
        points.append(ForecastPoint(day, Money(opening.amount + scheduled_total + usual,
                                               opening.currency)))
        day += timedelta(days=1)
        elapsed += 1
    return Forecast(today, end, opening, tuple(points), placed, usual_income, usual_spending,
                    history_months)


def usual_flow(total: Money, months: int, scheduled_monthly: Sequence[Money]) -> Money:
    """Average per month beyond what is scheduled (never below zero)."""
    if months <= 0:
        return Money.zero(total.currency)
    average = total.amount / months
    for value in scheduled_monthly:
        average -= value.amount
    average = max(average, Decimal(0)).quantize(_CENT, rounding=ROUND_HALF_UP)
    return Money(average, total.currency)
