"""The largest and smallest amounts pass through every feature exactly.

Totals may exceed the largest amount a person can type (e.g. two maximum
incomes); computed values must still work everywhere (statistics, analysis,
goals, subscriptions, investments, AI context, backups, CSV).
"""

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from money_manager.ai.context import build_financial_context
from money_manager.core.errors import ValidationError
from money_manager.domain.entities import TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.money import MAX_ABS_AMOUNT, Money
from money_manager.domain.periods import DateRange
from money_manager.services import AppServices
from money_manager.services.data_service import RESET_CONFIRMATION
from tests.services.support import TODAY

MAX = str(MAX_ABS_AMOUNT)  # 999,999,999,999.99


@pytest.fixture
def huge(app_services: AppServices) -> AppServices:
    s = app_services
    bank = s.accounts.create("Bank", opening_balance=MAX, opening_date=date(2026, 1, 1))
    salary = s.categories.create("Salary", CategoryKind.INCOME)
    food = s.categories.create("Food", CategoryKind.EXPENSE)
    stocks = s.categories.create("Stocks", CategoryKind.EXPENSE)
    s.categories.set_investment(stocks.id, True)
    for month in (3, 4, 5, 6):
        s.transactions.create(TransactionDraft(bank.id, TransactionType.INCOME, MAX,
                                               date(2026, month, 1), salary.id, description="Pay"))
        s.transactions.create(TransactionDraft(bank.id, TransactionType.EXPENSE, "0.01",
                                               date(2026, month, 2), food.id, description="Gum"))
    s.allocations.create("Vault", initial_amount=MAX)
    s.goals.create_with_new_allocation("Island", target=MAX, initial_amount=MAX)
    s.subscriptions.create("Yacht", amount=MAX, frequency="weekly",
                           next_payment_date=TODAY + timedelta(days=2), category_id=food.id,
                           account_id=bank.id)
    fund = s.investments.create("Fund", "etf")
    s.investments.add_contribution(fund.investment.id, MAX, date(2026, 6, 3),
                                   account_id=bank.id, category_id=stocks.id)
    s.investments.add_contribution(fund.investment.id, MAX, date(2026, 6, 4))
    s.investments.set_value(fund.investment.id, MAX, TODAY)
    return s


def test_totals_beyond_the_input_limit_are_exact(huge: AppServices) -> None:
    max_money = Money(MAX_ABS_AMOUNT)
    total = huge.balances.total_balance()
    # opening + 4 incomes − 4 × 0.01 − one contribution
    assert total == Money(MAX_ABS_AMOUNT * 5 - Decimal("0.04") - MAX_ABS_AMOUNT)

    summary = huge.allocations.summary()
    assert summary.total_balance == total
    assert summary.available == total - max_money - max_money

    report = huge.statistics.report(DateRange(date(2026, 1, 1), TODAY))
    assert report.totals.income == Money(MAX_ABS_AMOUNT * 4)
    assert report.totals.investments == max_money
    assert report.totals.spending == Money("0.04")

    analysis = huge.analysis.analyze(DateRange(date(2026, 1, 1), TODAY))
    assert analysis.savings_amount == Money(MAX_ABS_AMOUNT * 4 - Decimal("0.04"))
    assert "3,999,999,999,999.96" in build_financial_context(analysis).text

    overview = huge.dashboard.overview()
    assert overview.total_balance == total

    [goal] = huge.goals.list()
    assert goal.is_complete and goal.progress == Decimal(1)

    [subscription] = huge.subscriptions.list()
    assert subscription.monthly_cost == Money(
        (MAX_ABS_AMOUNT * 52 / 12).quantize(Decimal("0.01")))
    assert huge.subscriptions.statistics().yearly_total == Money(MAX_ABS_AMOUNT * 52)

    portfolio = huge.investments.summary()
    assert portfolio.net_invested == Money(MAX_ABS_AMOUNT * 2)
    assert portfolio.total_profit == -max_money  # valued at MAX after investing 2 × MAX


def test_the_largest_amounts_survive_a_backup(huge: AppServices, tmp_path: Path) -> None:
    before = huge.balances.total_balance()
    path = tmp_path / "backup.json"
    huge.data.export_backup(path)
    huge.data.reset(RESET_CONFIRMATION)
    huge.data.import_backup(path)
    assert huge.balances.total_balance() == before
    assert huge.data.export_transactions_csv(tmp_path / "t.csv") == 9


def test_amounts_above_the_limit_are_refused(huge: AppServices) -> None:
    bank = huge.accounts.list()[0]
    salary = huge.categories.list(CategoryKind.INCOME)[0]
    with pytest.raises(ValidationError, match="must not exceed"):
        huge.transactions.create(TransactionDraft(bank.id, TransactionType.INCOME,
                                                  "1000000000000.00", TODAY, salary.id))
    with pytest.raises(ValidationError, match="at most 2 decimal places"):
        huge.transactions.create(TransactionDraft(bank.id, TransactionType.INCOME, "0.001",
                                                  TODAY, salary.id))


def test_one_centime_is_exact_everywhere(app_services: AppServices) -> None:
    s = app_services
    bank = s.accounts.create("Bank", opening_balance="0.01", opening_date=date(2026, 1, 1))
    food = s.categories.create("Food", CategoryKind.EXPENSE)
    salary = s.categories.create("Salary", CategoryKind.INCOME)
    for _ in range(3):
        s.transactions.create(TransactionDraft(bank.id, TransactionType.INCOME, "0.10", TODAY,
                                               salary.id))
    s.transactions.create(TransactionDraft(bank.id, TransactionType.EXPENSE, "0.20", TODAY,
                                           food.id))
    # 0.1 + 0.1 + 0.1 − 0.2 is exactly 0.1: no binary floating-point drift.
    assert s.balances.total_balance() == Money("0.11")
    report = s.statistics.report(DateRange(TODAY, TODAY))
    assert report.totals.savings == Money("0.10")
    assert report.totals.savings_rate == Decimal("0.3333")
