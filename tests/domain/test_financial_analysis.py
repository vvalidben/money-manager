"""Pure financial-health engine: periods, trends, unusual spending, facts, export."""

from datetime import date
from decimal import Decimal

import pytest

from money_manager.domain.analytics import (
    Cadence,
    ExpenseRecord,
    LedgerEntry,
    RecurringExpense,
    TrendDirection,
)
from money_manager.domain.enums import TransactionType
from money_manager.domain.financial_analysis import (
    MonthValue,
    UnusualKind,
    baseline_ranges,
    comparison_range,
    detect_unusual_spending,
    month_end_balances,
    percent_text,
    recurring_analysis,
    trend_months,
    trend_of,
)
from money_manager.domain.money import Money
from money_manager.domain.periods import DateRange

EXPENSE = TransactionType.EXPENSE
FOOD, TRAVEL, STOCKS, RENT = 1, 2, 3, 4
NAMES = {FOOD: "Food", TRAVEL: "Travel", STOCKS: "Stocks", RENT: "Rent"}
INVEST = frozenset({STOCKS})
JUNE = DateRange(date(2026, 6, 1), date(2026, 6, 30))


def m(value: str) -> Money:
    return Money.of(value)


def spend(day: date, category: int, amount: str) -> LedgerEntry:
    return LedgerEntry(day, EXPENSE, category, Money.of(amount).minor_units)


def record(day: date, category: int, amount: str, text: str = "") -> ExpenseRecord:
    return ExpenseRecord(day, text, category, Money.of(amount).minor_units)


class TestPeriods:
    @pytest.mark.parametrize(
        ("period", "expected"),
        [
            # month to date → same days of the previous month
            (DateRange(date(2026, 9, 1), date(2026, 9, 27)),
             DateRange(date(2026, 8, 1), date(2026, 8, 27))),
            # 31st clamps to a shorter previous month
            (DateRange(date(2026, 3, 1), date(2026, 3, 30)),
             DateRange(date(2026, 2, 1), date(2026, 2, 28))),
            # a whole month → the whole previous month
            (JUNE, DateRange(date(2026, 5, 1), date(2026, 5, 31))),
            (DateRange(date(2026, 3, 1), date(2026, 3, 31)),
             DateRange(date(2026, 2, 1), date(2026, 2, 28))),
            # anything else → the equally long period just before
            (DateRange(date(2026, 6, 10), date(2026, 6, 19)),
             DateRange(date(2026, 5, 31), date(2026, 6, 9))),
            (DateRange(date(2026, 5, 1), date(2026, 6, 30)),
             DateRange(date(2026, 3, 1), date(2026, 4, 30))),
        ],
    )
    def test_comparison_range(self, period: DateRange, expected: DateRange) -> None:
        assert comparison_range(period) == expected

    def test_baseline_ranges(self) -> None:
        period = DateRange(date(2026, 6, 21), date(2026, 6, 30))
        assert baseline_ranges(period) == (
            DateRange(date(2026, 6, 11), date(2026, 6, 20)),
            DateRange(date(2026, 6, 1), date(2026, 6, 10)),
            DateRange(date(2026, 5, 22), date(2026, 5, 31)),
        )

    def test_trend_months_use_complete_months_since_tracking(self) -> None:
        assert trend_months(date(2026, 9, 27), date(2025, 1, 1)) == tuple(
            date(2026, month, 1) for month in range(3, 9))  # Mar–Aug; September is partial
        assert trend_months(date(2026, 8, 31), date(2025, 1, 1))[-1] == date(2026, 8, 1)
        assert trend_months(date(2026, 9, 27), date(2026, 7, 15)) == (
            date(2026, 7, 1), date(2026, 8, 1))
        assert trend_months(date(2026, 9, 27), None) == ()


class TestTrends:
    @staticmethod
    def series(*values: str) -> list[MonthValue]:
        return [MonthValue(date(2026, i + 1, 1), m(v)) for i, v in enumerate(values)]

    def test_rising_falling_stable(self) -> None:
        rising = trend_of(self.series("100", "100", "100", "150", "150", "150"))
        falling = trend_of(self.series("200", "200", "100", "100"))
        stable = trend_of(self.series("100", "104"))

        assert (rising.direction, rising.change) == (TrendDirection.RISING, Decimal("0.5000"))
        assert (falling.direction, falling.change) == (TrendDirection.FALLING, Decimal("-0.5000"))
        assert (stable.direction, stable.change) == (TrendDirection.STABLE, Decimal("0.0400"))

    def test_odd_length_compares_equal_halves(self) -> None:
        # 5 months: oldest 2 vs newest 2, the middle month is not used.
        trend = trend_of(self.series("100", "100", "999", "110", "110"))
        assert trend.change == Decimal("0.1000")

    def test_negative_balances_use_the_size_of_the_old_average(self) -> None:
        trend = trend_of(self.series("-200", "-100"))
        assert (trend.direction, trend.change) == (TrendDirection.RISING, Decimal("0.5000"))

    def test_not_enough_data(self) -> None:
        assert trend_of(self.series("100")).direction is TrendDirection.NO_DATA
        assert trend_of([]).direction is TrendDirection.NO_DATA

    def test_from_zero(self) -> None:
        assert trend_of(self.series("0", "50")).direction is TrendDirection.RISING
        zero = trend_of(self.series("0", "0"))
        assert (zero.direction, zero.change) == (TrendDirection.STABLE, Decimal(0))

    def test_month_end_balances(self) -> None:
        changes = {date(2026, 1, 1): 100000, date(2026, 1, 31): -2500, date(2026, 2, 1): 1}
        balances = month_end_balances(changes, [date(2026, 1, 1), date(2026, 2, 1)], "MAD")
        assert [b.value for b in balances] == [m("975"), m("975.01")]


class TestUnusualSpending:
    @staticmethod
    def history(amount: str = "300") -> list[LedgerEntry]:
        """Food spending in each of the three 30-day baseline periods before June."""
        return [spend(date(2026, 5, 20), FOOD, amount), spend(date(2026, 4, 20), FOOD, amount),
                spend(date(2026, 3, 20), FOOD, amount)]

    def detect(self, entries, records=(), tracking_start=date(2026, 1, 1)):
        return detect_unusual_spending(entries, list(records), JUNE, NAMES, INVEST, "MAD",
                                       tracking_start)

    def test_category_spike(self) -> None:
        found = self.detect([*self.history(), spend(date(2026, 6, 10), FOOD, "600")])

        [spike] = found
        assert spike.kind is UnusualKind.CATEGORY_SPIKE
        assert (spike.amount, spike.baseline, spike.factor) == (m("600"), m("300"), Decimal("2.00"))

    def test_below_the_spike_ratio(self) -> None:
        assert self.detect([*self.history(), spend(date(2026, 6, 10), FOOD, "449.99")]) == ()

    def test_small_increases_relative_to_total_spending_are_ignored(self) -> None:
        steady_rent = [spend(date(2026, month, 11), RENT, "5000") for month in (3, 4, 5, 6)]
        entries = [*self.history("10"), spend(date(2026, 6, 10), FOOD, "20"), *steady_rent]
        # Food doubled, but +10 MAD is far below 5 % of this month's spending.
        assert [u.category_name for u in self.detect(entries)] == []

    def test_new_category(self) -> None:
        entries = [*self.history(), spend(date(2026, 6, 5), FOOD, "300"),
                   spend(date(2026, 6, 20), TRAVEL, "2200")]

        [new] = self.detect(entries)

        assert (new.kind, new.category_name, new.factor) == (UnusualKind.NEW_CATEGORY, "Travel",
                                                             None)

    def test_small_new_category_is_ignored(self) -> None:
        entries = [*self.history(), spend(date(2026, 6, 5), FOOD, "300"),
                   spend(date(2026, 6, 6), TRAVEL, "20")]
        assert self.detect(entries) == ()

    def test_without_history_nothing_is_flagged(self) -> None:
        assert self.detect([spend(date(2026, 6, 10), FOOD, "9999")]) == ()

    def test_investments_are_not_spending(self) -> None:
        entries = [*self.history(), spend(date(2026, 6, 5), FOOD, "300"),
                   spend(date(2026, 6, 6), STOCKS, "50000")]
        assert self.detect(entries) == ()

    def test_large_single_expense(self) -> None:
        records = [record(date(2026, 5, d), FOOD, "100") for d in range(1, 11)]
        records.append(record(date(2026, 6, 12), FOOD, "450", "New sofa"))
        entries = [*self.history("1000"), spend(date(2026, 6, 12), FOOD, "450"),
                   spend(date(2026, 6, 13), FOOD, "500")]

        [large] = self.detect(entries, records)

        assert (large.kind, large.amount, large.baseline) == (UnusualKind.LARGE_EXPENSE,
                                                              m("450"), m("100"))
        assert (large.factor, large.day, large.description) == (Decimal("4.50"),
                                                                date(2026, 6, 12), "New sofa")

    def test_large_expense_needs_enough_history(self) -> None:
        records = [record(date(2026, 5, d), FOOD, "100") for d in range(1, 3)]  # only 2
        records.append(record(date(2026, 6, 12), FOOD, "450"))
        entries = [*self.history("1000"), spend(date(2026, 6, 12), FOOD, "450")]
        assert self.detect(entries, records) == ()

    def test_large_expense_is_compared_within_its_own_category(self) -> None:
        # Rent is always 5,000 while food expenses are ~100: rent is not unusual.
        records = [record(date(2026, 5, d), FOOD, "100") for d in range(1, 11)]
        records += [record(date(2026, month, 10), RENT, "5000") for month in (3, 4, 5, 6)]
        entries = [*self.history("1000"),
                   *(spend(date(2026, month, 10), RENT, "5000") for month in (3, 4, 5, 6)),
                   spend(date(2026, 6, 13), FOOD, "1000")]
        assert self.detect(entries, records) == ()

    def test_periods_before_tracking_are_not_a_baseline(self) -> None:
        # Tracking began on 2 May: only the May period is complete and holds the
        # regular 300, so June's 300 is normal (not diluted by untracked periods).
        entries = [*self.history(), spend(date(2026, 6, 10), FOOD, "300")]
        assert self.detect(entries, tracking_start=date(2026, 5, 2)) == ()
        # Without a single complete earlier period nothing is compared.
        assert self.detect(entries, tracking_start=date(2026, 5, 20)) == ()
        assert self.detect(entries, tracking_start=None) == ()

    def test_spike_uses_only_tracked_baselines(self) -> None:
        entries = [spend(date(2026, 5, 20), FOOD, "300"), spend(date(2026, 6, 10), FOOD, "600")]
        # Over all three periods the average would be 100 (factor 6); only May counts.
        [spike] = self.detect(entries, tracking_start=date(2026, 5, 2))
        assert (spike.baseline, spike.factor) == (m("300"), Decimal("2.00"))


class TestRecurring:
    NETFLIX = RecurringExpense("Netflix", FOOD, Cadence.MONTHLY, m("65"), 4, date(2026, 3, 3),
                               date(2026, 6, 3), date(2026, 7, 3), m("65"), True)
    MARKET = RecurringExpense("Market", FOOD, Cadence.WEEKLY, m("100"), 6, date(2026, 5, 1),
                              date(2026, 6, 5), date(2026, 6, 12), m("433.33"), True)

    def test_untracked_and_share(self) -> None:
        result = recurring_analysis([self.NETFLIX, self.MARKET], [" netflix "], m("65"),
                                    m("4983.30"))

        assert result.detected_monthly_total == m("498.33")
        assert [r.label for r in result.untracked] == ["Market"]
        assert result.share_of_monthly_spending == Decimal("0.1000")

    def test_without_spending_history(self) -> None:
        result = recurring_analysis([self.NETFLIX], [], m("0"), None)
        assert result.share_of_monthly_spending is None and len(result.untracked) == 1


def test_percent_text() -> None:
    assert percent_text(Decimal("0.18")) == "18.0%"
    assert percent_text(Decimal("0.1805"), signed=True) == "+18.1%"
    assert percent_text(Decimal("-0.05"), signed=True) == "-5.0%"


def test_history_fixture_covers_each_baseline_period_once() -> None:
    days = [entry.day for entry in TestUnusualSpending.history()]
    periods = baseline_ranges(JUNE)
    assert [sum(day in period for day in days) for period in periods] == [1, 1, 1]
