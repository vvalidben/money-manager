"""The cash-flow forecast (today is 15 Jun 2026 in the tests)."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

import pytest

from money_manager.domain.entities import Account, TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.forecast import EventKind
from money_manager.domain.money import Money
from money_manager.services import AppServices

DAYS_PER_MONTH = Decimal(365) / 12


def usual(monthly: str, days: int) -> Decimal:
    return (Decimal(monthly) / DAYS_PER_MONTH * days).quantize(Decimal("0.01"), ROUND_HALF_UP)


@pytest.fixture
def history(app_services: AppServices) -> Account:
    """March–May: 9,000 income and 6,000 spending a month; balance 10,000 today."""
    bank = app_services.accounts.create("Bank", opening_balance="1000",
                                        opening_date=date(2026, 3, 1))
    salary = app_services.categories.create("Salary", CategoryKind.INCOME)
    rent = app_services.categories.create("Rent", CategoryKind.EXPENSE)
    for month in (3, 4, 5):
        app_services.transactions.create(TransactionDraft(
            bank.id, TransactionType.INCOME, "9000", date(2026, month, 1), salary.id))
        app_services.transactions.create(TransactionDraft(
            bank.id, TransactionType.EXPENSE, "6000", date(2026, month, 5), rent.id))
    return bank


def test_nothing_without_accounts(app_services: AppServices) -> None:
    assert app_services.forecast.forecast() is None


def test_scheduled_items_and_usual_spending(app_services: AppServices, history: Account) -> None:
    salary = app_services.categories.list(CategoryKind.INCOME)[0]
    food = app_services.categories.create("Food", CategoryKind.EXPENSE)
    app_services.recurring.create("Salary", type="income", amount="9000",
                                  account_id=history.id, category_id=salary.id,
                                  frequency="monthly", first_date=date(2026, 7, 1))
    app_services.subscriptions.create("Netflix", amount="65", frequency="monthly",
                                      next_payment_date=date(2026, 6, 10), category_id=food.id)
    app_services.debts.create("Sami", direction="lent", amount="1000",
                              start_date=date(2026, 6, 1), due_date=date(2026, 8, 1))

    forecast = app_services.forecast.forecast()
    assert forecast is not None
    assert (forecast.start, forecast.end) == (date(2026, 6, 15), date(2026, 12, 14))
    assert forecast.history_months == 3
    assert forecast.usual_income == Money.of("0")  # the salary is scheduled already
    assert forecast.usual_spending == Money.of("5935")  # 6,000 − Netflix 65
    assert forecast.opening == Money.of("10000")
    assert forecast.points[0].balance == Money.of("9935")  # Netflix, overdue, counts today
    kinds = [e.kind for e in forecast.events]
    assert kinds.count(EventKind.RECURRING) == 6 and kinds.count(EventKind.LOAN) == 1
    netflix = [e for e in forecast.events if e.kind is EventKind.SUBSCRIPTION]
    assert netflix[0].day == date(2026, 6, 15)  # overdue: counted today
    assert netflix[0].amount == Money.of("-65") and len(netflix) == 7  # 10 Jun … 10 Dec
    july_first = next(p for p in forecast.points if p.day == date(2026, 7, 1))
    assert july_first.balance == Money(Decimal("10000") - 65 + 9000 - usual("5935", 16))
    loan = next(e for e in forecast.events if e.kind is EventKind.LOAN)
    assert (loan.day, loan.label, loan.amount) == (date(2026, 8, 1), "Sami repays",
                                                   Money.of("1000"))


def test_money_gets_tight(app_services: AppServices, history: Account) -> None:
    forecast = app_services.forecast.forecast()
    assert forecast is not None
    # 9,000 income a month is "usual" here (nothing scheduled): it stays positive.
    assert forecast.first_below_zero is None and forecast.tight_months == ()
    assert forecast.closing > forecast.opening

    big = app_services.categories.create("Car", CategoryKind.EXPENSE)
    app_services.recurring.create("Car loan", type="expense", amount="12000",
                                  account_id=history.id, category_id=big.id,
                                  frequency="monthly", first_date=date(2026, 7, 5))
    forecast = app_services.forecast.forecast()
    assert forecast is not None
    low = forecast.first_below_zero
    # Usual income (9,000) keeps up for two payments of 12,000, not the third.
    assert low is not None and low.day == date(2026, 9, 5)
    assert forecast.tight_months[0] == date(2026, 9, 1)
    assert forecast.lowest.balance <= low.balance


def test_without_complete_months(app_services: AppServices) -> None:
    app_services.accounts.create("Bank", opening_balance="500", opening_date=date(2026, 6, 2))
    forecast = app_services.forecast.forecast(3)
    assert forecast is not None and forecast.history_months == 0
    assert forecast.usual_spending == Money.zero() and forecast.closing == Money.of("500")
    assert forecast.end == date(2026, 9, 14)
