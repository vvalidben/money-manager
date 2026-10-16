"""Recurring subscriptions: schedules, cost equivalents and statistics (pure).

Rules
-----
* A subscription is a *schedule*; it never creates transactions by itself.
  The user confirms each due date as paid (creating one real expense) or
  skipped. Each due date can be confirmed only once.
* Dates never drift: monthly, quarterly and yearly schedules keep their
  billing day (``anchor_day``), clamped to short months — 31 Jan → 28 Feb →
  31 Mar. Weekly schedules add seven days.
* Monthly equivalent = amount × payments per year ÷ 12 (weekly 52, monthly 12,
  quarterly 4, yearly 1), exact ``Decimal`` rounded half-up to the centime per
  subscription; totals add the rounded figures so rows and totals agree.
  Yearly equivalent = amount × payments per year (exact).
"""

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from money_manager.domain.health import ratio
from money_manager.domain.money import Money, sum_money
from money_manager.domain.periods import add_months, month_end

_CENT = Decimal("0.01")
MAX_OCCURRENCES_PER_SUBSCRIPTION = 60  # guards the upcoming list against runaway schedules


class Frequency(StrEnum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"

    @property
    def payments_per_year(self) -> int:
        return _PAYMENTS_PER_YEAR[self]

    @property
    def months_between(self) -> int | None:
        """Calendar months between payments; None for weekly schedules."""
        return _MONTHS_BETWEEN.get(self)


_PAYMENTS_PER_YEAR = {
    Frequency.WEEKLY: 52,
    Frequency.MONTHLY: 12,
    Frequency.QUARTERLY: 4,
    Frequency.YEARLY: 1,
}
_MONTHS_BETWEEN = {Frequency.MONTHLY: 1, Frequency.QUARTERLY: 3, Frequency.YEARLY: 12}


class PaymentStatus(StrEnum):
    PAID = "paid"
    SKIPPED = "skipped"


def advance(day: date, frequency: Frequency, anchor_day: int) -> date:
    """The payment date after ``day``."""
    months = frequency.months_between
    if months is None:
        return day + timedelta(days=7)
    first = add_months(day, months)
    return first.replace(day=min(anchor_day, month_end(first).day))


def occurrences(start: date, frequency: Frequency, anchor_day: int, until: date,
                limit: int = MAX_OCCURRENCES_PER_SUBSCRIPTION) -> list[date]:
    """Payment dates from ``start`` up to and including ``until`` (at most ``limit``)."""
    dates: list[date] = []
    day = start
    while day <= until and len(dates) < limit:
        dates.append(day)
        day = advance(day, frequency, anchor_day)
    return dates


@dataclass(frozen=True, slots=True)
class Subscription:
    id: int
    name: str
    amount: Money
    frequency: Frequency
    next_payment_date: date  # next payment not yet recorded or skipped
    anchor_day: int
    category_id: int
    account_id: int | None
    is_active: bool
    notes: str

    @property
    def monthly_cost(self) -> Money:
        exact = self.amount.amount * self.frequency.payments_per_year / 12
        return Money(exact.quantize(_CENT, rounding=ROUND_HALF_UP), self.amount.currency)

    @property
    def yearly_cost(self) -> Money:
        return Money(self.amount.amount * self.frequency.payments_per_year, self.amount.currency)



@dataclass(frozen=True, slots=True)
class UpcomingPayment:
    subscription: Subscription
    due_date: date
    today: date

    @property
    def amount(self) -> Money:
        return self.subscription.amount

    @property
    def days_until(self) -> int:
        return (self.due_date - self.today).days

    @property
    def is_overdue(self) -> bool:
        return self.due_date < self.today

    @property
    def can_be_confirmed(self) -> bool:
        """Only the oldest unconfirmed date of a subscription can be confirmed next."""
        return self.due_date == self.subscription.next_payment_date


def upcoming_payments(
    subscriptions: Iterable[Subscription], today: date, horizon_days: int
) -> tuple[UpcomingPayment, ...]:
    """Unconfirmed past dates plus scheduled ones up to ``today + horizon_days``, by date."""
    until = today + timedelta(days=horizon_days)
    items = [
        UpcomingPayment(subscription, due, today)
        for subscription in subscriptions
        if subscription.is_active
        for due in occurrences(subscription.next_payment_date, subscription.frequency,
                               subscription.anchor_day, until)
    ]
    items.sort(key=lambda p: (p.due_date, p.subscription.name.casefold()))
    return tuple(items)


@dataclass(frozen=True, slots=True)
class CostShare:
    key: str  # category id (as text) or frequency value
    name: str
    monthly_cost: Money
    share: Decimal | None
    count: int


@dataclass(frozen=True, slots=True)
class SubscriptionStats:
    subscriptions: tuple[Subscription, ...]
    upcoming: tuple[UpcomingPayment, ...]
    by_category: tuple[CostShare, ...]
    by_frequency: tuple[CostShare, ...]
    currency: str
    horizon_days: int

    @property
    def active(self) -> tuple[Subscription, ...]:
        return tuple(s for s in self.subscriptions if s.is_active)

    @property
    def inactive_count(self) -> int:
        return len(self.subscriptions) - len(self.active)

    @property
    def monthly_total(self) -> Money:
        return sum_money((s.monthly_cost for s in self.active), self.currency)

    @property
    def yearly_total(self) -> Money:
        return sum_money((s.yearly_cost for s in self.active), self.currency)

    @property
    def most_expensive(self) -> Subscription | None:
        """Highest monthly equivalent among active subscriptions."""
        active = sorted(self.active, key=lambda s: (-s.monthly_cost.minor_units, s.name.casefold()))
        return active[0] if active else None

    @property
    def upcoming_total(self) -> Money:
        return sum_money((p.amount for p in self.upcoming if not p.is_overdue), self.currency)

    @property
    def overdue(self) -> tuple[UpcomingPayment, ...]:
        return tuple(p for p in self.upcoming if p.is_overdue)


def subscription_stats(
    subscriptions: Sequence[Subscription],
    category_names: Mapping[int, str],
    today: date,
    horizon_days: int,
    currency: str,
) -> SubscriptionStats:
    active = [s for s in subscriptions if s.is_active]
    total = sum_money((s.monthly_cost for s in active), currency)

    def shares(groups: Mapping[str, list[Subscription]], names: Mapping[str, str]) -> tuple[CostShare, ...]:
        rows = []
        for key, members in groups.items():
            cost = sum_money((s.monthly_cost for s in members), currency)
            rows.append(CostShare(key, names[key], cost, ratio(cost, total), len(members)))
        rows.sort(key=lambda r: (-r.monthly_cost.minor_units, r.name.casefold()))
        return tuple(rows)

    by_category: defaultdict[str, list[Subscription]] = defaultdict(list)
    by_frequency: defaultdict[str, list[Subscription]] = defaultdict(list)
    for subscription in active:
        by_category[str(subscription.category_id)].append(subscription)
        by_frequency[subscription.frequency.value].append(subscription)

    return SubscriptionStats(
        subscriptions=tuple(subscriptions),
        upcoming=upcoming_payments(subscriptions, today, horizon_days),
        by_category=shares(
            by_category,
            {key: category_names.get(int(key), "?") for key in by_category},
        ),
        by_frequency=shares(by_frequency, {key: key.capitalize() for key in by_frequency}),
        currency=currency,
        horizon_days=horizon_days,
    )
