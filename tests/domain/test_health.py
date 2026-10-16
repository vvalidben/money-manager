from datetime import date
from decimal import Decimal

import pytest

from money_manager.domain.health import (
    HealthLevel,
    assess_runway,
    assess_savings_rate,
    assess_spending_change,
    ratio,
    runway_months,
    savings_rate,
    spending_change,
)
from money_manager.domain.money import Money
from money_manager.domain.periods import (
    DateRange,
    add_months,
    month_end,
    month_to_date,
    same_days_previous_month,
)


def m(value: str) -> Money:
    return Money.of(value)


class TestRatios:
    def test_ratio_is_exact_and_rounded_half_up(self) -> None:
        assert ratio(m("1"), m("3")) == Decimal("0.3333")
        assert ratio(m("2"), m("3")) == Decimal("0.6667")
        assert ratio(m("0.01"), m("1000")) == Decimal("0.0000")  # 0.00001 rounds away
        assert ratio(m("1"), m("0")) is None

    def test_savings_rate(self) -> None:
        assert savings_rate(m("12000"), m("7420")) == Decimal("0.3817")
        assert savings_rate(m("1000"), m("1500")) == Decimal("-0.5000")
        assert savings_rate(m("0"), m("100")) is None

    def test_spending_change(self) -> None:
        assert spending_change(m("110"), m("100")) == Decimal("0.1000")
        assert spending_change(m("50"), m("100")) == Decimal("-0.5000")
        assert spending_change(m("50"), m("0")) is None

    def test_runway(self) -> None:
        assert runway_months(m("34500"), m("7420")) == Decimal("4.6")
        assert runway_months(m("-10"), m("100")) == Decimal(0)
        assert runway_months(m("100"), None) is None
        assert runway_months(m("100"), m("0")) is None


class TestAssessments:
    @pytest.mark.parametrize(
        ("rate", "level"),
        [(None, HealthLevel.UNKNOWN), (Decimal("0.2"), HealthLevel.GOOD),
         (Decimal("0.1999"), HealthLevel.FAIR), (Decimal("0"), HealthLevel.FAIR),
         (Decimal("-0.01"), HealthLevel.POOR)],
    )
    def test_savings(self, rate: Decimal | None, level: HealthLevel) -> None:
        assert assess_savings_rate(rate) is level

    @pytest.mark.parametrize(
        ("change", "level"),
        [(None, HealthLevel.UNKNOWN), (Decimal("-0.2"), HealthLevel.GOOD),
         (Decimal("0"), HealthLevel.GOOD), (Decimal("0.1"), HealthLevel.FAIR),
         (Decimal("0.1001"), HealthLevel.POOR)],
    )
    def test_spending(self, change: Decimal | None, level: HealthLevel) -> None:
        assert assess_spending_change(change) is level

    @pytest.mark.parametrize(
        ("months", "level"),
        [(None, HealthLevel.UNKNOWN), (Decimal(6), HealthLevel.GOOD),
         (Decimal("5.9"), HealthLevel.FAIR), (Decimal(3), HealthLevel.FAIR),
         (Decimal("2.9"), HealthLevel.POOR)],
    )
    def test_runway(self, months: Decimal | None, level: HealthLevel) -> None:
        assert assess_runway(months) is level


class TestPeriods:
    def test_month_helpers(self) -> None:
        assert month_end(date(2024, 2, 10)) == date(2024, 2, 29)
        assert add_months(date(2026, 1, 31), -1) == date(2025, 12, 1)
        assert add_months(date(2026, 11, 5), 3) == date(2027, 2, 1)
        assert month_to_date(date(2026, 6, 15)) == DateRange(date(2026, 6, 1), date(2026, 6, 15))

    @pytest.mark.parametrize(
        ("today", "expected"),
        [
            (date(2026, 6, 15), (date(2026, 5, 1), date(2026, 5, 15))),
            (date(2026, 3, 31), (date(2026, 2, 1), date(2026, 2, 28))),  # clamped
            (date(2026, 1, 10), (date(2025, 12, 1), date(2025, 12, 10))),
        ],
    )
    def test_same_days_previous_month(self, today: date, expected: tuple[date, date]) -> None:
        period = same_days_previous_month(today)
        assert (period.start, period.end) == expected

    def test_date_range(self) -> None:
        period = DateRange(date(2026, 6, 1), date(2026, 6, 15))
        assert period.days == 15
        assert date(2026, 6, 15) in period and date(2026, 6, 16) not in period
        with pytest.raises(ValueError):
            DateRange(date(2026, 6, 2), date(2026, 6, 1))
