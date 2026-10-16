"""Pure analytics: every calculation checked on hand-built ledger rows."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from money_manager.domain.analytics import (
    BalanceTrend,
    Cadence,
    ExpenseRecord,
    Granularity,
    LedgerEntry,
    TrendDirection,
    balance_changes,
    balance_trend,
    bucket_ranges,
    category_changes,
    detect_recurring,
    granularity_for,
    monthly_summaries,
    period_totals,
    spending_by_category,
    spending_trend,
)
from money_manager.domain.enums import TransactionType
from money_manager.domain.money import Money
from money_manager.domain.periods import DateRange, StatsRange, previous_range, rolling_range

INCOME, EXPENSE = TransactionType.INCOME, TransactionType.EXPENSE
ADJ_IN, ADJ_OUT = TransactionType.ADJUSTMENT_IN, TransactionType.ADJUSTMENT_OUT
FOOD, RENT, STOCKS, SALARY = 1, 2, 3, 4
NAMES = {FOOD: "Food", RENT: "Rent", STOCKS: "Stocks", SALARY: "Salary"}
INVEST = frozenset({STOCKS})
NONE: frozenset[int] = frozenset()
JUNE = DateRange(date(2026, 6, 1), date(2026, 6, 30))


def e(day: date, type_: TransactionType, category: int | None, amount: str) -> LedgerEntry:
    return LedgerEntry(day, type_, category, Money.of(amount).minor_units)


def m(value: str) -> Money:
    return Money.of(value)


# ------------------------------------------------------------------ ranges


class TestRanges:
    TODAY = date(2026, 6, 15)

    @pytest.mark.parametrize(
        ("preset", "start"),
        [
            (StatsRange.DAYS_7, date(2026, 6, 9)),
            (StatsRange.DAYS_30, date(2026, 5, 17)),
            (StatsRange.MONTHS_3, date(2026, 3, 16)),
            (StatsRange.MONTHS_6, date(2025, 12, 16)),
            (StatsRange.YEAR_1, date(2025, 6, 16)),
        ],
    )
    def test_rolling_ranges_end_today(self, preset: StatsRange, start: date) -> None:
        assert rolling_range(preset, self.TODAY) == DateRange(start, self.TODAY)

    def test_day_counts(self) -> None:
        assert rolling_range(StatsRange.DAYS_7, self.TODAY).days == 7
        assert rolling_range(StatsRange.DAYS_30, self.TODAY).days == 30

    def test_month_ranges_clamp_short_months(self) -> None:
        # 31 May minus 3 months is 28 Feb (clamped); the range starts the next day.
        assert rolling_range(StatsRange.MONTHS_3, date(2026, 5, 31)).start == date(2026, 3, 1)

    def test_custom_has_no_preset(self) -> None:
        with pytest.raises(ValueError):
            rolling_range(StatsRange.CUSTOM, self.TODAY)

    def test_previous_range_is_adjacent_and_equally_long(self) -> None:
        period = DateRange(date(2026, 6, 1), date(2026, 6, 30))
        previous = previous_range(period)
        assert previous == DateRange(date(2026, 5, 2), date(2026, 5, 31))
        assert previous.days == period.days


# ------------------------------------------------------------ period totals


class TestPeriodTotals:
    def test_definitions(self) -> None:
        entries = [
            e(date(2026, 6, 1), INCOME, SALARY, "12000"),
            e(date(2026, 6, 2), EXPENSE, RENT, "4500"),
            e(date(2026, 6, 3), EXPENSE, FOOD, "1830"),
            e(date(2026, 6, 4), EXPENSE, STOCKS, "2000"),
            e(date(2026, 6, 5), ADJ_IN, None, "10"),
            e(date(2026, 6, 6), ADJ_OUT, None, "4"),
        ]

        totals = period_totals(entries, JUNE, INVEST, "MAD")

        assert totals.income == m("12000")
        assert totals.expenses == m("8330")
        assert totals.investments == m("2000")
        assert totals.spending == m("6330")
        assert totals.savings == m("5670")  # income − spending; investing counts as saving
        assert totals.net_change == m("3676")  # 12000 − 8330 + 10 − 4
        assert totals.savings_rate == Decimal("0.4725")
        assert totals.investment_rate == Decimal("0.1667")

    def test_without_investment_categories_everything_is_spending(self) -> None:
        totals = period_totals([e(date(2026, 6, 4), EXPENSE, STOCKS, "2000")], JUNE, NONE, "MAD")

        assert (totals.investments, totals.spending) == (m("0"), m("2000"))

    def test_empty(self) -> None:
        totals = period_totals([], JUNE, INVEST, "MAD")

        assert totals.income.is_zero() and totals.expenses.is_zero()
        assert totals.savings.is_zero() and totals.net_change.is_zero()
        assert totals.savings_rate is None and totals.investment_rate is None

    def test_zero_income(self) -> None:
        totals = period_totals([e(date(2026, 6, 3), EXPENSE, FOOD, "50")], JUNE, NONE, "MAD")

        assert totals.savings == m("-50")
        assert totals.savings_rate is None  # undefined without income
        assert totals.investment_rate is None

    def test_zero_expenses(self) -> None:
        totals = period_totals([e(date(2026, 6, 3), INCOME, SALARY, "900")], JUNE, NONE, "MAD")

        assert totals.savings == m("900")
        assert totals.savings_rate == Decimal("1.0000")
        assert totals.investment_rate == Decimal("0.0000")

    def test_date_boundaries_are_inclusive(self) -> None:
        entries = [
            e(date(2026, 5, 31), INCOME, SALARY, "1"),  # day before: excluded
            e(date(2026, 6, 1), INCOME, SALARY, "10"),  # first day: included
            e(date(2026, 6, 30), INCOME, SALARY, "100"),  # last day: included
            e(date(2026, 7, 1), INCOME, SALARY, "1000"),  # day after: excluded
        ]

        assert period_totals(entries, JUNE, NONE, "MAD").income == m("110")

    def test_decimal_precision(self) -> None:
        entries = [e(date(2026, 6, 1), EXPENSE, FOOD, "0.10") for _ in range(3)]
        entries.append(e(date(2026, 6, 2), INCOME, SALARY, "0.30"))

        totals = period_totals(entries, JUNE, NONE, "MAD")

        assert totals.savings == m("0.00")
        assert totals.savings_rate == Decimal("0.0000")

    def test_rates_round_half_up(self) -> None:
        # 1/3 saved → 0.33333… → 0.3333; 2/3 → 0.6667
        totals = period_totals(
            [e(date(2026, 6, 1), INCOME, SALARY, "3"), e(date(2026, 6, 1), EXPENSE, FOOD, "2")],
            JUNE, NONE, "MAD",
        )
        assert totals.savings_rate == Decimal("0.3333")


# --------------------------------------------------------------- categories


class TestCategories:
    def test_breakdown_excludes_investments_and_sorts(self) -> None:
        entries = [
            e(date(2026, 6, 2), EXPENSE, FOOD, "300"),
            e(date(2026, 6, 3), EXPENSE, FOOD, "200"),
            e(date(2026, 6, 4), EXPENSE, RENT, "1500"),
            e(date(2026, 6, 5), EXPENSE, STOCKS, "9999"),
            e(date(2026, 5, 31), EXPENSE, FOOD, "7777"),  # outside the range
        ]

        rows = spending_by_category(entries, JUNE, NAMES, INVEST, "MAD")

        assert [(r.name, r.amount, r.share) for r in rows] == [
            ("Rent", m("1500"), Decimal("0.7500")),
            ("Food", m("500"), Decimal("0.2500")),
        ]

    def test_ties_are_ordered_by_name(self) -> None:
        entries = [e(date(2026, 6, 2), EXPENSE, RENT, "5"), e(date(2026, 6, 2), EXPENSE, FOOD, "5")]

        assert [r.name for r in spending_by_category(entries, JUNE, NAMES, NONE, "MAD")] == [
            "Food", "Rent"
        ]

    def test_requirements_example_food_plus_22_percent(self) -> None:
        may, june = DateRange(date(2026, 5, 1), date(2026, 5, 31)), JUNE
        entries = [e(date(2026, 5, 10), EXPENSE, FOOD, "1500"),
                   e(date(2026, 6, 10), EXPENSE, FOOD, "1830")]

        [food] = category_changes(entries, june, may, NAMES, NONE, "MAD")

        assert (food.previous, food.current, food.change) == (m("1500"), m("1830"), m("330"))
        assert food.change_ratio == Decimal("0.2200")

    def test_new_and_disappeared_categories(self) -> None:
        may = DateRange(date(2026, 5, 1), date(2026, 5, 31))
        entries = [e(date(2026, 5, 10), EXPENSE, RENT, "100"),
                   e(date(2026, 6, 10), EXPENSE, FOOD, "40")]

        changes = {c.name: c for c in category_changes(entries, JUNE, may, NAMES, NONE, "MAD")}

        assert changes["Food"].is_new and changes["Food"].change_ratio is None
        assert changes["Rent"].change_ratio == Decimal("-1.0000")
        assert [c.name for c in category_changes(entries, JUNE, may, NAMES, NONE, "MAD")] == [
            "Rent", "Food"  # biggest movement first
        ]


# ------------------------------------------------------------------ months


class TestMonthlySummaries:
    def test_month_over_month(self) -> None:
        entries = [
            e(date(2026, 3, 5), EXPENSE, FOOD, "1000"),
            e(date(2026, 3, 1), INCOME, SALARY, "5000"),
            e(date(2026, 4, 5), EXPENSE, FOOD, "1250"),
            e(date(2026, 4, 1), INCOME, SALARY, "5000"),
            e(date(2026, 5, 5), EXPENSE, FOOD, "1000"),
        ]

        april, may = monthly_summaries(entries, date(2026, 4, 1), date(2026, 5, 31), NONE, "MAD")

        assert april.month == date(2026, 4, 1) and not april.is_partial
        assert april.spending_change == Decimal("0.2500")
        assert april.income_change == Decimal("0.0000")
        assert may.spending_change == Decimal("-0.2000")
        assert may.income_change == Decimal("-1.0000")
        assert may.totals.savings_rate is None

    def test_partial_month_compares_same_days(self) -> None:
        entries = [
            e(date(2026, 5, 10), EXPENSE, FOOD, "100"),  # within 1–15 May: baseline
            e(date(2026, 5, 20), EXPENSE, FOOD, "900"),  # after the 15th: not compared
            e(date(2026, 6, 3), EXPENSE, FOOD, "150"),
        ]

        [june] = monthly_summaries(entries, date(2026, 6, 1), date(2026, 6, 15), NONE, "MAD")

        assert june.is_partial
        assert june.spending_change == Decimal("0.5000")

    def test_no_baseline(self) -> None:
        [june] = monthly_summaries(
            [e(date(2026, 6, 3), EXPENSE, FOOD, "1")], date(2026, 6, 1), date(2026, 6, 30),
            NONE, "MAD",
        )
        assert june.spending_change is None and june.income_change is None


# ------------------------------------------------------------------- trend


class TestTrend:
    @pytest.mark.parametrize(
        ("days", "granularity"),
        [(1, Granularity.DAY), (31, Granularity.DAY), (32, Granularity.WEEK),
         (186, Granularity.WEEK), (187, Granularity.MONTH)],
    )
    def test_granularity(self, days: int, granularity: Granularity) -> None:
        start = date(2026, 1, 1)
        assert granularity_for(DateRange(start, start + timedelta(days=days - 1))) is granularity

    def test_week_buckets_start_on_monday_and_are_clipped(self) -> None:
        period = DateRange(date(2026, 6, 3), date(2026, 6, 16))  # Wednesday .. Tuesday

        buckets = bucket_ranges(period, Granularity.WEEK)

        assert [(b.start, b.end) for b in buckets] == [
            (date(2026, 6, 3), date(2026, 6, 7)),
            (date(2026, 6, 8), date(2026, 6, 14)),
            (date(2026, 6, 15), date(2026, 6, 16)),
        ]

    def test_month_buckets(self) -> None:
        period = DateRange(date(2025, 11, 20), date(2026, 1, 5))
        assert [(b.start, b.end) for b in bucket_ranges(period, Granularity.MONTH)] == [
            (date(2025, 11, 20), date(2025, 11, 30)),
            (date(2025, 12, 1), date(2025, 12, 31)),
            (date(2026, 1, 1), date(2026, 1, 5)),
        ]

    def test_buckets_add_up_and_exclude_investments(self) -> None:
        period = DateRange(date(2026, 6, 1), date(2026, 6, 10))
        entries = [e(date(2026, 6, d), EXPENSE, FOOD, "10.01") for d in range(1, 11)]
        entries.append(e(date(2026, 6, 5), EXPENSE, STOCKS, "500"))

        trend = spending_trend(entries, period, INVEST, "MAD")

        assert trend.granularity is Granularity.DAY and len(trend.buckets) == 10
        assert sum(b.spending.minor_units for b in trend.buckets) == 10010
        assert trend.average_per_day == m("10.01")
        assert trend.direction is TrendDirection.STABLE and trend.change == Decimal("0.0000")

    def test_rising_and_falling(self) -> None:
        period = DateRange(date(2026, 6, 1), date(2026, 6, 10))
        rising = [e(date(2026, 6, 2), EXPENSE, FOOD, "10"), e(date(2026, 6, 8), EXPENSE, FOOD, "30")]
        falling = [e(date(2026, 6, 2), EXPENSE, FOOD, "30"), e(date(2026, 6, 8), EXPENSE, FOOD, "10")]

        up = spending_trend(rising, period, NONE, "MAD")
        down = spending_trend(falling, period, NONE, "MAD")

        assert (up.direction, up.change) == (TrendDirection.RISING, Decimal("2.0000"))
        assert (down.direction, down.change) == (TrendDirection.FALLING, Decimal("-0.6667"))

    def test_uneven_halves_use_daily_averages(self) -> None:
        # 7 days: first half 3 days, second half 4 days; equal daily spend is stable.
        period = DateRange(date(2026, 6, 1), date(2026, 6, 7))
        entries = [e(date(2026, 6, d), EXPENSE, FOOD, "7") for d in range(1, 8)]

        assert spending_trend(entries, period, NONE, "MAD").direction is TrendDirection.STABLE

    def test_no_spending(self) -> None:
        trend = spending_trend([], JUNE, NONE, "MAD")
        assert trend.direction is TrendDirection.NO_DATA and trend.change is None
        assert trend.average_per_day == m("0")

    def test_spending_only_in_second_half_is_rising(self) -> None:
        trend = spending_trend([e(date(2026, 6, 30), EXPENSE, FOOD, "5")], JUNE, NONE, "MAD")
        assert trend.direction is TrendDirection.RISING and trend.change is None


# ----------------------------------------------------------------- balance


class TestBalance:
    def test_trend_counts_openings_on_their_date(self) -> None:
        changes = balance_changes(
            [(date(2026, 5, 20), 100000), (date(2026, 6, 2), 5000)],
            [(date(2026, 5, 25), -2500), (date(2026, 6, 3), 1000), (date(2026, 7, 1), 99)],
        )

        trend = balance_trend(changes, DateRange(date(2026, 6, 1), date(2026, 6, 3)), "MAD")

        assert trend.opening == m("975")
        assert [p.balance for p in trend.points] == [m("975"), m("1025"), m("1035")]
        assert trend.closing == m("1035")
        assert trend.change == m("60")
        assert trend.change_ratio == Decimal("0.0615")

    def test_before_any_account(self) -> None:
        trend = balance_trend({}, DateRange(date(2026, 6, 1), date(2026, 6, 2)), "MAD")
        assert isinstance(trend, BalanceTrend)
        assert trend.opening.is_zero() and trend.change_ratio is None


# --------------------------------------------------------------- recurring


def r(day: date, description: str, amount: str, category: int | None = FOOD) -> ExpenseRecord:
    return ExpenseRecord(day, description, category, Money.of(amount).minor_units)


class TestRecurring:
    AS_OF = date(2026, 6, 15)

    def test_monthly_subscription(self) -> None:
        records = [r(date(2026, month, 3), "Netflix", "65") for month in (3, 4, 5, 6)]

        [found] = detect_recurring(records, self.AS_OF, "MAD")

        assert (found.label, found.cadence, found.occurrences) == ("Netflix", Cadence.MONTHLY, 4)
        assert found.typical_amount == m("65") and found.monthly_cost == m("65")
        assert found.is_fixed_amount
        assert found.next_expected == date(2026, 7, 4)  # last + median gap (31 days)

    def test_description_is_matched_ignoring_case_and_spaces(self) -> None:
        records = [r(date(2026, 4, 1), "gym  membership", "200"),
                   r(date(2026, 5, 1), "Gym Membership", "200"),
                   r(date(2026, 6, 1), "GYM MEMBERSHIP ", "200")]

        [found] = detect_recurring(records, self.AS_OF, "MAD")

        assert found.label == "GYM MEMBERSHIP"

    def test_weekly_monthly_cost_is_exact(self) -> None:
        records = [r(date(2026, 5, 18) + timedelta(weeks=w), "Market", "100.00") for w in range(4)]

        [found] = detect_recurring(records, self.AS_OF, "MAD")

        assert found.cadence is Cadence.WEEKLY
        assert found.monthly_cost == m("433.33")  # 100 × 52 ÷ 12, rounded half-up

    def test_variable_amounts_use_the_median(self) -> None:
        records = [r(date(2026, 3, 10), "Electricity", "300"),
                   r(date(2026, 4, 10), "Electricity", "420"),
                   r(date(2026, 5, 10), "Electricity", "350"),
                   r(date(2026, 6, 10), "Electricity", "310")]

        [found] = detect_recurring(records, self.AS_OF, "MAD")

        assert found.typical_amount == m("330")  # median of 300, 310, 350, 420
        assert not found.is_fixed_amount

    @pytest.mark.parametrize(
        "records",
        [
            [r(date(2026, 5, 1), "Netflix", "65"), r(date(2026, 6, 1), "Netflix", "65")],  # too few
            [r(date(2026, d, 1), "Coffee", "20") for d in (1, 3, 6)],  # irregular gaps
            [r(date(2026, d, 5), "Shopping", a) for d, a in ((4, "50"), (5, "500"), (6, "60"))],
            [r(date(2026, d, 3), "Old gym", "150") for d in (1, 2, 3)],  # stopped in March
            [r(date(2026, d, 3), "", "65") for d in (4, 5, 6)],  # undescribed
        ],
    )
    def test_not_recurring(self, records: list[ExpenseRecord]) -> None:
        assert detect_recurring(records, self.AS_OF, "MAD") == ()

    def test_same_description_in_different_categories_is_separate(self) -> None:
        records = [r(date(2026, d, 3), "Payment", "10", FOOD) for d in (4, 5, 6)]
        records += [r(date(2026, d, 3), "Payment", "10", RENT) for d in (4, 6)]

        found = detect_recurring(records, self.AS_OF, "MAD")

        assert [(f.category_id, f.occurrences) for f in found] == [(FOOD, 3)]

    def test_sorted_by_monthly_cost(self) -> None:
        records = [r(date(2026, d, 3), "Netflix", "65") for d in (4, 5, 6)]
        records += [r(date(2026, d, 5), "Rent", "4500", RENT) for d in (4, 5, 6)]

        assert [f.label for f in detect_recurring(records, self.AS_OF, "MAD")] == ["Rent", "Netflix"]
