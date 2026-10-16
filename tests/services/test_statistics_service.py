"""Statistics end to end on a real database, cross-checked with other services."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import event

from money_manager.core.errors import ValidationError
from money_manager.domain.analytics import Cadence, Granularity
from money_manager.domain.entities import Account, Category, TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.money import Money
from money_manager.domain.periods import DateRange, StatsRange
from money_manager.persistence.database import Database
from money_manager.services import (
    AccountService,
    BalanceService,
    CategoryService,
    StatisticsService,
    TransactionService,
)
from tests.services.support import TODAY, fixed_today

JUNE_TO_DATE = DateRange(date(2026, 6, 1), TODAY)


@pytest.fixture
def statistics(database: Database) -> StatisticsService:
    return StatisticsService(database, today=fixed_today)


@pytest.fixture
def bank(accounts: AccountService) -> Account:
    return accounts.create("Bank", opening_balance="10000", opening_date=date(2025, 1, 1))


@pytest.fixture
def record(transactions: TransactionService, bank: Account):
    def _record(type_: TransactionType, amount: str, category: Category | None, on: date,
                description: str = "") -> None:
        transactions.create(TransactionDraft(
            bank.id, type_, amount, on, None if category is None else category.id,
            description=description))
    return _record


@pytest.fixture
def stocks(categories: CategoryService) -> Category:
    category = categories.create("Stocks", CategoryKind.EXPENSE)
    return categories.set_investment(category.id, True)


def test_empty_database(statistics: StatisticsService) -> None:
    report = statistics.report(statistics.range_for(StatsRange.DAYS_30))

    assert not report.has_accounts
    assert report.totals.income.is_zero() and report.totals.expenses.is_zero()
    assert report.totals.savings_rate is None and report.totals.investment_rate is None
    assert report.balance.opening.is_zero() and report.balance.closing.is_zero()
    assert len(report.balance.points) == 30
    assert report.spending_by_category == () and report.category_changes == ()
    assert report.recurring == ()
    assert report.income_change is None


def test_one_transaction(
    statistics: StatisticsService, record, food: Category
) -> None:
    record(TransactionType.EXPENSE, "42.50", food, TODAY)

    report = statistics.report(statistics.range_for(StatsRange.DAYS_7))

    assert report.totals.expenses == Money.of("42.50")
    assert [(c.name, c.share) for c in report.spending_by_category] == [("Food", Decimal("1.0000"))]
    assert report.balance.change == Money.of("-42.50")
    [change] = report.category_changes
    assert change.is_new
    assert report.trend.granularity is Granularity.DAY


def test_multiple_months_and_month_over_month(
    statistics: StatisticsService, record, salary: Category, food: Category
) -> None:
    record(TransactionType.INCOME, "5000", salary, date(2026, 3, 1))
    record(TransactionType.EXPENSE, "1500", food, date(2026, 3, 20))
    record(TransactionType.INCOME, "5000", salary, date(2026, 4, 1))
    record(TransactionType.EXPENSE, "1830", food, date(2026, 4, 20))
    record(TransactionType.INCOME, "5200", salary, date(2026, 5, 1))
    record(TransactionType.EXPENSE, "1200", food, date(2026, 5, 20))

    report = statistics.report(DateRange(date(2026, 4, 1), date(2026, 5, 31)))

    assert [s.month for s in report.months] == [date(2026, 4, 1), date(2026, 5, 1)]
    april, may = report.months
    assert april.spending_change == Decimal("0.2200")  # 1,500 → 1,830: +22 %
    assert may.spending_change == Decimal("-0.3443")
    assert may.income_change == Decimal("0.0400")
    assert report.totals.income == Money.of("10200")
    assert report.totals.savings == Money.of("7170")
    assert report.totals.savings_rate == Decimal("0.7029")


def test_date_boundaries(
    statistics: StatisticsService, record, food: Category
) -> None:
    record(TransactionType.EXPENSE, "1", food, date(2026, 5, 31))
    record(TransactionType.EXPENSE, "10", food, date(2026, 6, 1))
    record(TransactionType.EXPENSE, "100", food, TODAY)

    report = statistics.report(JUNE_TO_DATE)

    assert report.totals.expenses == Money.of("110")
    assert report.previous_period == DateRange(date(2026, 5, 17), date(2026, 5, 31))
    assert report.previous_totals.expenses == Money.of("1")


def test_investments_are_saving_not_spending(
    statistics: StatisticsService, record, salary: Category, food: Category, stocks: Category
) -> None:
    record(TransactionType.INCOME, "10000", salary, date(2026, 6, 1))
    record(TransactionType.EXPENSE, "3000", food, date(2026, 6, 2))
    record(TransactionType.EXPENSE, "2000", stocks, date(2026, 6, 3))

    totals = statistics.report(JUNE_TO_DATE).totals

    assert totals.expenses == Money.of("5000")
    assert totals.investments == Money.of("2000")
    assert totals.spending == Money.of("3000")
    assert totals.savings == Money.of("7000")
    assert totals.savings_rate == Decimal("0.7000")
    assert totals.investment_rate == Decimal("0.2000")


def test_investment_categories_are_not_listed_as_spending(
    statistics: StatisticsService, record, food: Category, stocks: Category
) -> None:
    record(TransactionType.EXPENSE, "10", food, TODAY)
    record(TransactionType.EXPENSE, "500", stocks, TODAY)

    report = statistics.report(JUNE_TO_DATE)

    assert [c.name for c in report.spending_by_category] == ["Food"]
    assert report.has_investment_categories


def test_net_change_matches_balance_service(
    statistics: StatisticsService, balances: BalanceService, record, salary: Category,
    food: Category,
) -> None:
    record(TransactionType.INCOME, "1234.56", salary, date(2026, 4, 30))
    record(TransactionType.EXPENSE, "99.99", food, date(2026, 5, 3))
    record(TransactionType.ADJUSTMENT_OUT, "0.07", None, date(2026, 6, 2))
    period = DateRange(date(2026, 5, 1), TODAY)

    report = statistics.report(period)

    before = balances.total_balance(as_of=date(2026, 4, 30))
    after = balances.total_balance(as_of=TODAY)
    assert report.balance.opening == before
    assert report.balance.closing == after
    assert report.totals.net_change == after - before
    for point in report.balance.points:
        assert point.balance == balances.total_balance(as_of=point.day)


def test_recurring_uses_a_year_of_history(
    statistics: StatisticsService, record, categories: CategoryService
) -> None:
    subscriptions = categories.create("Subscriptions", CategoryKind.EXPENSE)
    for month in (3, 4, 5, 6):
        record(TransactionType.EXPENSE, "65", subscriptions, date(2026, month, 3), "Netflix")

    report = statistics.report(statistics.range_for(StatsRange.DAYS_7))  # 9–15 Jun only

    [netflix] = report.recurring
    assert (netflix.label, netflix.cadence) == ("Netflix", Cadence.MONTHLY)
    assert report.recurring_monthly_total == Money.of("65")


@pytest.mark.parametrize("preset", [p for p in StatsRange if p is not StatsRange.CUSTOM])
def test_every_preset_ends_today(statistics: StatisticsService, preset: StatsRange) -> None:
    assert statistics.range_for(preset).end == TODAY
    assert statistics.report(statistics.range_for(preset)).period.end == TODAY


class TestValidation:
    def test_future_end(self, statistics: StatisticsService) -> None:
        with pytest.raises(ValidationError, match="future"):
            statistics.report(DateRange(TODAY, TODAY + timedelta(days=1)))

    @pytest.mark.parametrize(
        ("start", "end", "field"),
        [
            (date(2026, 6, 2), date(2026, 6, 1), "start"),
            ("2026-06-01", TODAY, "start"),
            (date(1899, 12, 31), TODAY, "start"),
            (date(2010, 1, 1), TODAY, "start"),  # longer than ten years
        ],
    )
    def test_custom_range(
        self, statistics: StatisticsService, start: object, end: object, field: str
    ) -> None:
        with pytest.raises(ValidationError) as info:
            statistics.custom_range(start, end)
        assert info.value.field == field

    def test_valid_custom_range(self, statistics: StatisticsService) -> None:
        assert statistics.custom_range(date(2026, 1, 1), TODAY).days == 166


def test_query_count_is_constant(
    statistics: StatisticsService, database: Database, record, categories: CategoryService
) -> None:
    def count() -> int:
        statements: list[str] = []
        listener = lambda *args: statements.append(args[2])  # noqa: E731
        event.listen(database.engine, "before_cursor_execute", listener)
        try:
            statistics.report(statistics.range_for(StatsRange.YEAR_1))
        finally:
            event.remove(database.engine, "before_cursor_execute", listener)
        return len(statements)

    small = count()
    for index in range(40):
        category = categories.create(f"C{index}", CategoryKind.EXPENSE)
        record(TransactionType.EXPENSE, "1", category, date(2026, 1 + index % 5, 1 + index % 27))

    assert count() == small <= 6
