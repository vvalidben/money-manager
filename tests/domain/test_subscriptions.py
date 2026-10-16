from dataclasses import replace
from datetime import date

import pytest

from money_manager.core.errors import ValidationError
from money_manager.domain.entities import Category
from money_manager.domain.enums import CategoryKind
from money_manager.domain.money import Money
from money_manager.domain.subscriptions import (
    Frequency,
    Subscription,
    advance,
    occurrences,
    subscription_stats,
    upcoming_payments,
)
from money_manager.domain.validation import validate_subscription

TODAY = date(2026, 6, 15)
SUBS = Category(5, "Subscriptions", CategoryKind.EXPENSE)
NETFLIX = Subscription(1, "Netflix", Money.of("150"), Frequency.MONTHLY, date(2026, 6, 20), 20,
                       SUBS.id, None, True, "")


def sub(**overrides: object) -> Subscription:
    return replace(NETFLIX, **overrides)  # type: ignore[arg-type]


class TestSchedule:
    @pytest.mark.parametrize(
        ("frequency", "start", "anchor", "expected"),
        [
            (Frequency.WEEKLY, date(2026, 6, 29), 29, date(2026, 7, 6)),
            (Frequency.MONTHLY, date(2026, 1, 15), 15, date(2026, 2, 15)),
            (Frequency.MONTHLY, date(2026, 12, 5), 5, date(2027, 1, 5)),
            (Frequency.QUARTERLY, date(2026, 11, 30), 30, date(2027, 2, 28)),
            (Frequency.YEARLY, date(2026, 3, 1), 1, date(2027, 3, 1)),
        ],
    )
    def test_advance(self, frequency: Frequency, start: date, anchor: int, expected: date) -> None:
        assert advance(start, frequency, anchor) == expected

    def test_month_end_billing_does_not_drift(self) -> None:
        dates = occurrences(date(2026, 1, 31), Frequency.MONTHLY, 31, date(2026, 5, 31))

        assert dates == [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31),
                         date(2026, 4, 30), date(2026, 5, 31)]

    def test_leap_day_yearly(self) -> None:
        dates = occurrences(date(2024, 2, 29), Frequency.YEARLY, 29, date(2028, 12, 31))
        assert dates == [date(2024, 2, 29), date(2025, 2, 28), date(2026, 2, 28),
                         date(2027, 2, 28), date(2028, 2, 29)]

    def test_occurrences_are_capped(self) -> None:
        assert len(occurrences(date(2000, 1, 1), Frequency.WEEKLY, 1, date(2030, 1, 1),
                               limit=5)) == 5

class TestCosts:
    @pytest.mark.parametrize(
        ("frequency", "amount", "monthly", "yearly"),
        [
            (Frequency.MONTHLY, "150", "150.00", "1800.00"),
            (Frequency.YEARLY, "1200", "100.00", "1200.00"),
            (Frequency.YEARLY, "1000", "83.33", "1000.00"),  # 83.333… rounded half-up
            (Frequency.QUARTERLY, "300", "100.00", "1200.00"),
            (Frequency.WEEKLY, "100", "433.33", "5200.00"),  # 100 × 52 ÷ 12
            (Frequency.WEEKLY, "0.03", "0.13", "1.56"),  # 0.13 exactly
            (Frequency.YEARLY, "0.06", "0.01", "0.06"),  # 0.005 rounds half-up
        ],
    )
    def test_equivalents(self, frequency: Frequency, amount: str, monthly: str,
                         yearly: str) -> None:
        item = sub(frequency=frequency, amount=Money.of(amount))

        assert item.monthly_cost == Money.of(monthly)
        assert item.yearly_cost == Money.of(yearly)

    def test_requirements_examples_total(self) -> None:
        items = [
            sub(id=1, name="Netflix", amount=Money.of("150")),
            sub(id=2, name="Spotify", amount=Money.of("70")),
            sub(id=3, name="Internet", amount=Money.of("300")),
        ]

        stats = subscription_stats(items, {SUBS.id: "Subscriptions"}, TODAY, 30, "MAD")

        assert stats.monthly_total == Money.of("520")
        assert stats.yearly_total == Money.of("6240")


class TestUpcomingAndStats:
    def test_upcoming_includes_overdue_and_skips_inactive(self) -> None:
        items = [
            sub(id=1, name="Netflix", next_payment_date=date(2026, 6, 20)),
            sub(id=2, name="Gym", next_payment_date=date(2026, 6, 1), anchor_day=1),
            sub(id=3, name="Paused", is_active=False),
            sub(id=4, name="Weekly box", frequency=Frequency.WEEKLY,
                next_payment_date=date(2026, 6, 16), anchor_day=16),
        ]

        upcoming = upcoming_payments(items, TODAY, 21)

        # Horizon: 15 Jun + 21 days = 6 Jul. The paused subscription is left out.
        assert [(p.subscription.name, p.due_date) for p in upcoming] == [
            ("Gym", date(2026, 6, 1)),
            ("Weekly box", date(2026, 6, 16)),
            ("Netflix", date(2026, 6, 20)),
            ("Weekly box", date(2026, 6, 23)),
            ("Weekly box", date(2026, 6, 30)),
            ("Gym", date(2026, 7, 1)),
        ]
        first = upcoming[0]
        assert first.is_overdue and first.can_be_confirmed and first.days_until == -14
        assert not upcoming[-1].can_be_confirmed  # 1 Jul waits until 1 Jun is confirmed

    def test_statistics(self) -> None:
        items = [
            sub(id=1, name="Netflix", amount=Money.of("150")),
            sub(id=2, name="Domain", amount=Money.of("120"), frequency=Frequency.YEARLY,
                category_id=6, next_payment_date=date(2027, 1, 15), anchor_day=15),
            sub(id=3, name="Old", amount=Money.of("999"), is_active=False),
        ]

        stats = subscription_stats(items, {5: "Subscriptions", 6: "Hosting"}, TODAY, 30, "MAD")

        assert len(stats.active) == 2 and stats.inactive_count == 1
        assert stats.monthly_total == Money.of("160")
        assert stats.most_expensive is not None and stats.most_expensive.name == "Netflix"
        assert [(c.name, c.monthly_cost, str(c.share)) for c in stats.by_category] == [
            ("Subscriptions", Money.of("150"), "0.9375"),
            ("Hosting", Money.of("10"), "0.0625"),
        ]
        assert [c.name for c in stats.by_frequency] == ["Monthly", "Yearly"]
        assert stats.upcoming_total == Money.of("150")  # Netflix on 20 Jun

    def test_empty(self) -> None:
        stats = subscription_stats([], {}, TODAY, 30, "MAD")
        assert stats.monthly_total == Money.zero() and stats.most_expensive is None
        assert stats.by_category == () and stats.upcoming == ()


class TestValidation:
    def _validate(self, **overrides: object):
        fields: dict[str, object] = {
            "name": "Netflix", "amount": "150", "frequency": "monthly",
            "next_payment_date": date(2026, 6, 20), "category": SUBS, "notes": "",
        }
        fields.update(overrides)
        return validate_subscription(currency="MAD", today=TODAY, **fields)  # type: ignore[arg-type]

    def test_valid(self) -> None:
        valid = self._validate(frequency=" Yearly ", next_payment_date=date(2026, 1, 31))
        assert valid.frequency is Frequency.YEARLY and valid.anchor_day == 31

    @pytest.mark.parametrize(
        ("overrides", "field"),
        [
            ({"amount": "0"}, "amount"),
            ({"amount": "-10"}, "amount"),
            ({"amount": 9.99}, "amount"),
            ({"frequency": "daily"}, "frequency"),
            ({"next_payment_date": "2026-06-20"}, "next_payment_date"),
            ({"next_payment_date": date(2025, 6, 13)}, "next_payment_date"),
            ({"next_payment_date": date(2037, 1, 1)}, "next_payment_date"),
            ({"category": None}, "category_id"),
            ({"category": Category(7, "Salary", CategoryKind.INCOME)}, "category_id"),
            ({"category": replace(SUBS, is_archived=True)}, "category_id"),
            ({"name": " "}, "name"),
        ],
    )
    def test_invalid(self, overrides: dict[str, object], field: str) -> None:
        with pytest.raises(ValidationError) as info:
            self._validate(**overrides)
        assert info.value.field == field

    def test_recent_past_date_is_allowed(self) -> None:
        assert self._validate(next_payment_date=date(2026, 6, 1)).anchor_day == 1
