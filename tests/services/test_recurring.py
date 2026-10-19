"""Recurring entries: schedules that record income and expenses by themselves."""

from datetime import date

import pytest

from money_manager.core.errors import NotFoundError, ValidationError
from money_manager.domain.entities import Account, Category
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.money import Money
from money_manager.services import AppServices
from money_manager.services.recurring_service import RECURRING_NOTE

# Today is 15 Jun 2026 (tests.services.support).


@pytest.fixture
def bank(app_services: AppServices) -> Account:
    return app_services.accounts.create("Bank", opening_balance="1000",
                                        opening_date=date(2026, 1, 1))


@pytest.fixture
def salary(app_services: AppServices) -> Category:
    return app_services.categories.create("Salary", CategoryKind.INCOME)


@pytest.fixture
def rent(app_services: AppServices) -> Category:
    return app_services.categories.create("Rent", CategoryKind.EXPENSE)


def _salary(app_services: AppServices, bank: Account, salary: Category, first: date):
    return app_services.recurring.create("Salary", type="income", amount="9000",
                                         account_id=bank.id, category_id=salary.id,
                                         frequency="monthly", first_date=first)


def test_records_every_date_that_has_come(app_services: AppServices, bank: Account,
                                          salary: Category) -> None:
    entry = _salary(app_services, bank, salary, date(2026, 4, 1))
    outcome = app_services.recurring.record_due()
    assert outcome.recorded == 3 and outcome.problems == ()
    recorded = sorted(app_services.transactions.list(), key=lambda t: t.occurred_on)
    assert [t.occurred_on for t in recorded] == [date(2026, 4, 1), date(2026, 5, 1),
                                                 date(2026, 6, 1)]
    assert {(t.type, t.amount, t.category_id, t.description, t.notes) for t in recorded} == {
        (TransactionType.INCOME, Money.of("9000"), salary.id, "Salary", RECURRING_NOTE)}
    assert app_services.recurring.get(entry.id).next_date == date(2026, 7, 1)
    assert app_services.recurring.record_due().recorded == 0  # never twice
    assert app_services.balances.balance(bank.id) == Money.of("28000")


def test_month_end_days_do_not_drift(app_services: AppServices, bank: Account,
                                     rent: Category) -> None:
    app_services.recurring.create("Rent", type="expense", amount="3000", account_id=bank.id,
                                  category_id=rent.id, frequency="monthly",
                                  first_date=date(2026, 1, 31))
    app_services.recurring.record_due()
    days = sorted(t.occurred_on for t in app_services.transactions.list())
    assert days == [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31),
                    date(2026, 4, 30), date(2026, 5, 31)]


def test_future_first_date_waits(app_services: AppServices, bank: Account,
                                 salary: Category) -> None:
    _salary(app_services, bank, salary, date(2026, 7, 1))
    assert app_services.recurring.record_due().recorded == 0
    assert app_services.transactions.list() == []


def test_paused_entries_skip_missed_dates(app_services: AppServices, bank: Account,
                                          salary: Category) -> None:
    entry = _salary(app_services, bank, salary, date(2026, 3, 1))
    app_services.recurring.set_active(entry.id, False)
    assert app_services.recurring.record_due().recorded == 0
    resumed = app_services.recurring.set_active(entry.id, True)
    assert resumed.next_date == date(2026, 7, 1)  # Mar–Jun were missed while paused
    assert app_services.recurring.record_due().recorded == 0


def test_a_problem_is_reported_and_retried(app_services: AppServices, bank: Account,
                                           salary: Category) -> None:
    entry = _salary(app_services, bank, salary, date(2026, 6, 1))
    app_services.categories.archive(salary.id)
    outcome = app_services.recurring.record_due()
    assert outcome.recorded == 0
    [problem] = outcome.problems
    assert (problem.entry_id, problem.due) == (entry.id, date(2026, 6, 1))
    assert "archived" in problem.message
    app_services.categories.restore(salary.id)
    assert app_services.recurring.record_due().recorded == 1


@pytest.mark.parametrize(("changes", "field"), [
    ({"description": "  "}, "description"),
    ({"type": "adjustment_in"}, "type"),
    ({"amount": "0"}, "amount"),
    ({"frequency": "daily"}, "frequency"),
    ({"first_date": date(2025, 1, 1)}, "first_date"),  # over a year ago
    ({"first_date": date(2032, 1, 1)}, "first_date"),
])
def test_validation(app_services: AppServices, bank: Account, salary: Category,
                    changes: dict[str, object], field: str) -> None:
    values: dict[str, object] = {"description": "Salary", "type": "income", "amount": "10",
                                 "account_id": bank.id, "category_id": salary.id,
                                 "frequency": "monthly", "first_date": date(2026, 6, 1)}
    values.update(changes)
    description = values.pop("description")
    with pytest.raises(ValidationError) as caught:
        app_services.recurring.create(description, **values)  # type: ignore[arg-type]
    assert caught.value.field == field


def test_category_must_match_the_type(app_services: AppServices, bank: Account,
                                      rent: Category) -> None:
    with pytest.raises(ValidationError, match="not an income category"):
        app_services.recurring.create("Salary", type="income", amount="10", account_id=bank.id,
                                      category_id=rent.id, frequency="monthly",
                                      first_date=date(2026, 6, 1))


def test_not_before_the_account_opened(app_services: AppServices, salary: Category) -> None:
    late = app_services.accounts.create("Cash", opening_balance="0",
                                        opening_date=date(2026, 6, 1))
    with pytest.raises(ValidationError, match="before the account was opened"):
        app_services.recurring.create("Salary", type="income", amount="10", account_id=late.id,
                                      category_id=salary.id, frequency="monthly",
                                      first_date=date(2026, 5, 1))


def test_update_and_delete_keep_recorded_entries(app_services: AppServices, bank: Account,
                                                 salary: Category) -> None:
    entry = _salary(app_services, bank, salary, date(2026, 6, 1))
    app_services.recurring.record_due()
    changed = app_services.recurring.update(entry.id, "Salary (new job)", type="income",
                                            amount="9500", account_id=bank.id,
                                            category_id=salary.id, frequency="monthly",
                                            next_date=date(2026, 7, 25))
    assert (changed.amount, changed.next_date, changed.anchor_day) == (
        Money.of("9500"), date(2026, 7, 25), 25)
    app_services.recurring.delete(entry.id)
    assert app_services.recurring.list() == []
    assert len(app_services.transactions.list()) == 1
    with pytest.raises(NotFoundError):
        app_services.recurring.delete(entry.id)


def test_weekly(app_services: AppServices, bank: Account, rent: Category) -> None:
    app_services.recurring.create("Market", type="expense", amount="150", account_id=bank.id,
                                  category_id=rent.id, frequency="weekly",
                                  first_date=date(2026, 6, 1))
    assert app_services.recurring.record_due().recorded == 3  # 1, 8 and 15 June
