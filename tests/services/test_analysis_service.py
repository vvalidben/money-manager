"""Financial-health engine end to end, cross-checked against other services."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import event

from money_manager.core.errors import ValidationError
from money_manager.domain.analytics import TrendDirection
from money_manager.domain.entities import Account, Category, TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.ai.context import build_financial_context
from money_manager.domain.financial_analysis import UnusualKind
from money_manager.domain.money import MAX_ABS_AMOUNT, Money
from money_manager.domain.periods import DateRange
from money_manager.persistence.database import Database
from money_manager.services import (
    AccountService,
    BalanceService,
    CategoryService,
    FinancialAnalysisService,
    StatisticsService,
    SubscriptionService,
    TransactionService,
)
from tests.services.support import TODAY, fixed_today

JUNE_TO_DATE = DateRange(date(2026, 6, 1), TODAY)  # compared with 1–15 May
SUBJECTIVE = ("good", "bad", "poor", "great", "worse", "better", "healthy", "unhealthy",
              "should", "must", "excellent", "terrible", "warning")


@pytest.fixture
def analysis(database: Database) -> FinancialAnalysisService:
    return FinancialAnalysisService(database, today=fixed_today)


@pytest.fixture
def bank(accounts: AccountService) -> Account:
    return accounts.create("Bank", opening_balance="10000", opening_date=date(2025, 1, 1))


@pytest.fixture
def record(transactions: TransactionService, bank: Account):
    def _record(type_: TransactionType, amount: str, category: Category | None, on: date,
                description: str = "") -> None:
        transactions.create(TransactionDraft(bank.id, type_, amount, on,
                                             None if category is None else category.id,
                                             description=description))
    return _record


def facts_of(result) -> dict[str, str]:
    return {fact.code: fact.text for fact in result.facts}


def test_empty_database(analysis: FinancialAnalysisService) -> None:
    result = analysis.analyze()

    assert not result.has_accounts
    assert result.current_balance == Money.zero()
    assert result.period == JUNE_TO_DATE
    assert result.savings_rate is None and result.spending_ratio is None
    assert result.largest_expense_category is None
    assert result.unusual_spending == () and result.recurring.detected == ()
    assert result.income_trend.direction is TrendDirection.NO_DATA
    assert list(facts_of(result)) == ["balance", "net_change"]  # nothing else can be said


def test_requirements_example_structure(
    analysis: FinancialAnalysisService, record, salary: Category, food: Category,
    categories: CategoryService,
) -> None:
    rent = categories.create("Rent", CategoryKind.EXPENSE)
    record(TransactionType.INCOME, "12000", salary, date(2026, 5, 1))
    record(TransactionType.EXPENSE, "5000", food, date(2026, 5, 10))
    record(TransactionType.INCOME, "12000", salary, date(2026, 6, 1))
    record(TransactionType.EXPENSE, "4500", rent, date(2026, 6, 2))
    record(TransactionType.EXPENSE, "1400", food, date(2026, 6, 10))

    result = analysis.analyze()

    assert result.comparison_period == DateRange(date(2026, 5, 1), date(2026, 5, 15))
    assert (result.period_income, result.period_expenses) == (Money.of("12000"), Money.of("5900"))
    assert result.net_change == Money.of("6100")
    assert result.savings_amount == Money.of("6100")
    assert result.savings_rate == Decimal("0.5083")
    assert result.spending_ratio == Decimal("0.4917")
    assert result.expenses_change == Decimal("0.1800")  # 5,000 → 5,900
    assert result.largest_expense_category is not None
    assert result.largest_expense_category.name == "Rent"
    assert result.current_balance == Money.of("23100")  # 10,000 + 12,000 − 5,000 + 12,000 − 5,900
    facts = facts_of(result)
    assert facts["expenses_change"] == (
        "Expenses increased by 18.0% compared with 2026-05-01 to 2026-05-15 "
        "(5,000.00 MAD -> 5,900.00 MAD)."
    )
    assert facts["savings_rate"] == "Savings were 6,100.00 MAD, 50.8% of income."
    assert facts["largest_category"] == (
        "Largest spending category: Rent, 4,500.00 MAD (76.3% of spending).")


def test_no_income(analysis: FinancialAnalysisService, record, food: Category) -> None:
    record(TransactionType.EXPENSE, "250.75", food, date(2026, 6, 3))

    result = analysis.analyze()

    assert result.savings_rate is None and result.spending_ratio is None
    assert result.investment_rate is None
    assert facts_of(result)["no_income"] == (
        "No income was recorded while spending was 250.75 MAD.")


def test_no_expenses(analysis: FinancialAnalysisService, record, salary: Category) -> None:
    record(TransactionType.INCOME, "3000", salary, date(2026, 6, 3))

    result = analysis.analyze()

    assert result.savings_rate == Decimal("1.0000")
    assert result.spending_ratio == Decimal("0.0000")
    assert result.largest_expense_category is None
    assert "expenses_change" not in facts_of(result)


def test_negative_net_change(analysis: FinancialAnalysisService, record, salary: Category,
                             food: Category) -> None:
    record(TransactionType.INCOME, "1000", salary, date(2026, 6, 1))
    record(TransactionType.EXPENSE, "1660.50", food, date(2026, 6, 2))

    result = analysis.analyze()

    assert result.net_change == Money.of("-660.50")
    assert result.savings_amount == Money.of("-660.50")
    assert result.savings_rate == Decimal("-0.6605")
    assert result.spending_ratio == Decimal("1.6605")
    assert facts_of(result)["net_change"] == (
        "The balance changed by -660.50 MAD from 2026-06-01 to 2026-06-15.")


def test_positive_net_change_includes_adjustments(
    analysis: FinancialAnalysisService, balances: BalanceService, record, salary: Category,
) -> None:
    record(TransactionType.INCOME, "500", salary, date(2026, 6, 1))
    record(TransactionType.ADJUSTMENT_IN, "20", None, date(2026, 6, 2))

    result = analysis.analyze()

    assert result.net_change == Money.of("520")
    assert result.net_change == (balances.total_balance(as_of=TODAY)
                                 - balances.total_balance(as_of=date(2026, 5, 31)))
    assert facts_of(result)["net_change"].startswith("The balance changed by +520.00 MAD")


def test_multiple_categories_and_changes(
    analysis: FinancialAnalysisService, record, food: Category, categories: CategoryService,
) -> None:
    transport = categories.create("Transport", CategoryKind.EXPENSE)
    fun = categories.create("Fun", CategoryKind.EXPENSE)
    record(TransactionType.EXPENSE, "1500", food, date(2026, 5, 5))
    record(TransactionType.EXPENSE, "400", transport, date(2026, 5, 6))
    record(TransactionType.EXPENSE, "1830", food, date(2026, 6, 5))
    record(TransactionType.EXPENSE, "300", transport, date(2026, 6, 6))
    record(TransactionType.EXPENSE, "90", fun, date(2026, 6, 7))

    result = analysis.analyze()

    assert [c.name for c in result.spending_by_category] == ["Food", "Transport", "Fun"]
    changes = {c.name: c for c in result.category_changes}
    assert changes["Food"].change_ratio == Decimal("0.2200")
    assert changes["Transport"].change_ratio == Decimal("-0.2500")
    assert changes["Fun"].is_new
    facts = [f.text for f in result.facts if f.code.startswith("category_")]
    assert "Food spending increased by 22.0% (1,500.00 MAD -> 1,830.00 MAD)." in facts


def test_multiple_months_trends(analysis: FinancialAnalysisService, record, salary: Category,
                                food: Category) -> None:
    for month, income, spent in ((12, "5000", "2000"), (1, "5000", "2000"), (2, "5000", "2000"),
                                 (3, "6000", "3000"), (4, "6000", "3000"), (5, "6000", "3000")):
        year = 2025 if month == 12 else 2026
        record(TransactionType.INCOME, income, salary, date(year, month, 1))
        record(TransactionType.EXPENSE, spent, food, date(year, month, 15))

    result = analysis.analyze()

    assert [v.month for v in result.income_trend.series] == [
        date(2025, 12, 1), *(date(2026, m, 1) for m in range(1, 6))]
    assert (result.income_trend.direction, result.income_trend.change) == (
        TrendDirection.RISING, Decimal("0.2000"))
    assert (result.expense_trend.direction, result.expense_trend.change) == (
        TrendDirection.RISING, Decimal("0.5000"))
    assert result.balance_trend.direction is TrendDirection.RISING
    assert facts_of(result)["income_trend"] == (
        "Income over the last 6 complete months: rising (+20.0%, newer vs older half).")
    assert [m.month for m in result.monthly][-1] == date(2026, 6, 1)
    assert result.monthly[-1].is_partial


def test_unusual_spending_and_recurring(
    analysis: FinancialAnalysisService, record, food: Category, categories: CategoryService,
    database: Database, transactions: TransactionService,
) -> None:
    travel = categories.create("Travel", CategoryKind.EXPENSE)
    streaming = categories.create("Streaming", CategoryKind.EXPENSE)
    for month in (3, 4, 5, 6):
        record(TransactionType.EXPENSE, "65", streaming, date(2026, month, 3), "Netflix")
        record(TransactionType.EXPENSE, "300", food, date(2026, month, 12), "Groceries")
    record(TransactionType.EXPENSE, "2200", travel, date(2026, 6, 14), "Flight")
    SubscriptionService(database, transactions, today=fixed_today).create(
        "Netflix", amount="65", frequency="monthly", next_payment_date=date(2026, 7, 3),
        category_id=streaming.id)

    result = analysis.analyze(DateRange(date(2026, 5, 17), TODAY))  # 30 days

    kinds = {(u.kind, u.category_name) for u in result.unusual_spending}
    assert (UnusualKind.NEW_CATEGORY, "Travel") in kinds
    recurring = result.recurring
    assert {r.label for r in recurring.detected} == {"Netflix", "Groceries"}
    assert [r.label for r in recurring.untracked] == ["Groceries"]
    assert recurring.subscriptions_monthly_total == Money.of("65")
    assert "2 recurring expenses detected" in facts_of(result)["recurring"]


def test_large_numbers(analysis: FinancialAnalysisService, accounts: AccountService,
                       transactions: TransactionService, salary: Category,
                       food: Category) -> None:
    rich = accounts.create("Rich", opening_balance=MAX_ABS_AMOUNT, opening_date=date(2026, 1, 1))
    for day in (1, 2):
        transactions.create(TransactionDraft(rich.id, TransactionType.INCOME, MAX_ABS_AMOUNT,
                                             date(2026, 6, day), salary.id))
    transactions.create(TransactionDraft(rich.id, TransactionType.EXPENSE, "0.01",
                                         date(2026, 6, 3), food.id))

    result = analysis.analyze()

    assert result.period_income == Money(MAX_ABS_AMOUNT * 2)
    assert result.current_balance == Money(MAX_ABS_AMOUNT * 3 - Decimal("0.01"))
    assert result.savings_rate == Decimal("1.0000")  # 0.01 is invisible at 4 places
    assert "3,000,000,000,000.00" not in build_financial_context(result).text  # no overflow


def test_decimal_values(analysis: FinancialAnalysisService, record, salary: Category,
                        food: Category) -> None:
    for _ in range(3):
        record(TransactionType.INCOME, "0.10", salary, date(2026, 6, 2))
    record(TransactionType.EXPENSE, "0.10", food, date(2026, 6, 3))

    result = analysis.analyze()

    assert result.period_income == Money.of("0.30")
    assert result.savings_amount == Money.of("0.20")
    assert result.savings_rate == Decimal("0.6667")  # 0.2 ÷ 0.3, rounded half-up
    assert result.spending_ratio == Decimal("0.3333")


def test_date_boundaries(analysis: FinancialAnalysisService, record, food: Category) -> None:
    record(TransactionType.EXPENSE, "1", food, date(2026, 5, 31))  # day before
    record(TransactionType.EXPENSE, "10", food, date(2026, 6, 1))  # first day
    record(TransactionType.EXPENSE, "100", food, TODAY)  # last day
    record(TransactionType.EXPENSE, "1000", food, date(2026, 5, 15))  # last comparison day
    record(TransactionType.EXPENSE, "10000", food, date(2026, 5, 16))  # after comparison

    result = analysis.analyze()

    assert result.period_expenses == Money.of("110")
    assert result.comparison_totals.expenses == Money.of("1000")


def test_matches_the_statistics_page(analysis: FinancialAnalysisService, database: Database,
                                     record, salary: Category, food: Category) -> None:
    record(TransactionType.INCOME, "1234.56", salary, date(2026, 6, 2))
    record(TransactionType.EXPENSE, "99.99", food, date(2026, 6, 3))
    period = DateRange(date(2026, 5, 20), TODAY)

    result = analysis.analyze(period)
    report = StatisticsService(database, today=fixed_today).report(period)

    assert result.totals == report.totals
    assert result.spending_by_category == report.spending_by_category


def test_facts_are_neutral(analysis: FinancialAnalysisService, record, salary: Category,
                           food: Category) -> None:
    record(TransactionType.INCOME, "100", salary, date(2026, 5, 2))
    record(TransactionType.INCOME, "50", salary, date(2026, 6, 2))
    record(TransactionType.EXPENSE, "400", food, date(2026, 6, 3))

    for fact in analysis.analyze().facts:
        words = {w.strip(".,:;()").lower() for w in fact.text.split()}
        assert not words & set(SUBJECTIVE), fact.text
        assert any(ch.isdigit() for ch in fact.text), fact.text  # every fact is measurable


def test_ai_context_leaves_out_descriptions(analysis: FinancialAnalysisService, record,
                                            food: Category) -> None:
    for day in range(1, 11):
        record(TransactionType.EXPENSE, "100", food, date(2026, 5, day), "Weekly shop")
    record(TransactionType.EXPENSE, "2000", food, date(2026, 6, 10), "Private note: gift")
    result = analysis.analyze()
    assert any(u.kind is UnusualKind.LARGE_EXPENSE for u in result.unusual_spending)

    assert [u.description for u in result.unusual_spending
            if u.kind is UnusualKind.LARGE_EXPENSE] == ["Private note: gift"]
    text = build_financial_context(result).text

    assert "Private note" not in text and "Weekly shop" not in text
    assert "- Expenses: 2,000.00 MAD" in text  # June only


@pytest.mark.parametrize(
    ("period", "field"),
    [(DateRange(TODAY, date(2026, 6, 16)), "end"),
     (DateRange(date(1899, 1, 1), TODAY), "start"),
     (DateRange(date(2010, 1, 1), TODAY), "start")],
)
def test_invalid_periods(analysis: FinancialAnalysisService, period: DateRange,
                         field: str) -> None:
    with pytest.raises(ValidationError) as info:
        analysis.analyze(period)
    assert info.value.field == field


def test_query_count_is_constant(analysis: FinancialAnalysisService, database: Database,
                                 record, categories: CategoryService) -> None:
    def count() -> int:
        statements: list[str] = []
        listener = lambda *args: statements.append(args[2])  # noqa: E731
        event.listen(database.engine, "before_cursor_execute", listener)
        try:
            analysis.analyze()
        finally:
            event.remove(database.engine, "before_cursor_execute", listener)
        return len(statements)

    small = count()
    for index in range(30):
        category = categories.create(f"C{index}", CategoryKind.EXPENSE)
        record(TransactionType.EXPENSE, "5", category, date(2026, 1 + index % 5, 1 + index % 27))

    assert count() == small <= 8


def test_comparison_before_tracking_began_is_unavailable(
    analysis: FinancialAnalysisService, accounts: AccountService, database: Database,
    salary: Category, food: Category, transactions: TransactionService,
) -> None:
    # Tracking starts on 10 May, so 1–15 May is only partly recorded.
    late = accounts.create("Late", opening_balance="0", opening_date=date(2026, 5, 10))
    for type_, amount, category, on in ((TransactionType.EXPENSE, "100", food, date(2026, 5, 12)),
                                        (TransactionType.INCOME, "900", salary, date(2026, 6, 1)),
                                        (TransactionType.EXPENSE, "400", food, date(2026, 6, 2))):
        transactions.create(TransactionDraft(late.id, type_, amount, on, category.id))

    result = analysis.analyze()
    statistics = StatisticsService(database, today=fixed_today)
    # Statistics compare with the equal period just before: 17–31 May is tracked,
    # 24 Apr–19 May (before 20 May–15 June) is not.
    assert statistics.report(JUNE_TO_DATE).comparison_complete
    report = statistics.report(DateRange(date(2026, 5, 20), TODAY))

    assert not result.comparison_complete and result.tracking_start == date(2026, 5, 10)
    assert result.expenses_change is None and result.income_change is None
    facts = facts_of(result)
    assert "expenses_change" not in facts and "category_change" not in facts
    assert facts["comparison_unavailable"] == (
        "No comparison: the comparison period (2026-05-01 to 2026-05-15) starts before "
        "tracking began on 2026-05-10.")
    assert not report.comparison_complete
    assert report.expenses_change is None and report.category_changes == ()
    # 11–15 June compares with 6–10 June, entirely within tracked history.
    assert analysis.analyze(DateRange(date(2026, 6, 11), TODAY)).comparison_complete


def test_unchanged_income_reads_correctly(analysis: FinancialAnalysisService, record,
                                         salary: Category) -> None:
    record(TransactionType.INCOME, "5000", salary, date(2026, 5, 2))
    record(TransactionType.INCOME, "5000", salary, date(2026, 6, 2))
    assert facts_of(analysis.analyze())["income_change"].startswith("Income was unchanged")


def test_recurring_investments_are_not_recurring_spending(
    analysis: FinancialAnalysisService, record, categories: CategoryService, food: Category,
) -> None:
    stocks = categories.create("Stocks", CategoryKind.EXPENSE)
    categories.set_investment(stocks.id, True)
    for month in range(1, 7):
        record(TransactionType.EXPENSE, "2000", stocks, date(2026, month, 3), "ETF plan")
        record(TransactionType.EXPENSE, "65", food, date(2026, month, 4), "Streaming")

    detected = analysis.analyze().recurring.detected

    assert [item.label for item in detected] == ["Streaming"]
