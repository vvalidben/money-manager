"""Dashboard calculations, checked against independent services where possible."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import event

from money_manager.core.errors import CurrencyMismatchError
from money_manager.domain.entities import (
    Account,
    Category,
    TransactionDraft,
    TransactionFilter,
    TransactionQuery,
)
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.health import HealthLevel
from money_manager.domain.money import Money, sum_money
from money_manager.persistence.database import Database
from money_manager.services import (
    AccountService,
    AllocationService,
    AllocationTransferService,
    BalanceService,
    CategoryService,
    DashboardService,
    TransactionService,
)
from money_manager.services.dashboard_service import HISTORY_DAYS, OTHER_CATEGORY_LABEL
from tests.services.support import TODAY, AddTransaction, fixed_today

JUNE_1 = date(2026, 6, 1)


@pytest.fixture
def dashboard(database: Database) -> DashboardService:
    return DashboardService(database, today=fixed_today)


@pytest.fixture
def bank(accounts: AccountService) -> Account:
    # 29,920 + 12,000 − 7,420 = 34,500 (the example from the requirements)
    return accounts.create("Bank", opening_balance="29920", opening_date=date(2026, 1, 1))


@pytest.fixture
def rent(categories: CategoryService) -> Category:
    return categories.create("Rent", CategoryKind.EXPENSE)


def test_empty_database(dashboard: DashboardService) -> None:
    overview = dashboard.overview()

    assert not overview.has_accounts
    assert overview.total_balance == Money.zero()
    assert overview.balance_history == ()
    assert len(overview.monthly_flows) == 6
    assert all(f.income.is_zero() and f.expenses.is_zero() for f in overview.monthly_flows)
    assert overview.recent_transactions == ()
    assert overview.spending_by_category == ()
    assert [s.name for s in overview.allocation_slices] == ["Available"]
    health = overview.health
    assert (health.savings_level, health.spending_level, health.runway_level) == (
        HealthLevel.UNKNOWN, HealthLevel.UNKNOWN, HealthLevel.UNKNOWN
    )


def test_requirements_example(
    dashboard: DashboardService, bank: Account, salary: Category, food: Category, rent: Category,
    add: AddTransaction,
) -> None:
    add(TransactionType.INCOME, "12000", salary, on=JUNE_1, account_id=bank.id)
    add(TransactionType.EXPENSE, "4500", rent, on=date(2026, 6, 2), account_id=bank.id)
    add(TransactionType.EXPENSE, "2920", food, on=date(2026, 6, 10), account_id=bank.id)

    overview = dashboard.overview()

    assert (overview.period.start, overview.period.end) == (JUNE_1, TODAY)
    assert overview.total_balance == Money.of("34500")
    assert overview.income == Money.of("12000")
    assert overview.expenses == Money.of("7420")
    assert overview.savings == Money.of("4580")
    assert overview.health.savings_rate == Decimal("0.3817")


def test_adjustments_count_in_balance_but_not_as_income_or_spending(
    dashboard: DashboardService, bank: Account, add: AddTransaction
) -> None:
    add(TransactionType.ADJUSTMENT_IN, "80", on=JUNE_1, account_id=bank.id)
    add(TransactionType.ADJUSTMENT_OUT, "30", on=JUNE_1, account_id=bank.id)

    overview = dashboard.overview()

    assert overview.total_balance == Money.of("29970")
    assert overview.income.is_zero() and overview.expenses.is_zero()


def test_previous_month_comparison_uses_same_days(
    dashboard: DashboardService, bank: Account, food: Category, add: AddTransaction
) -> None:
    add(TransactionType.EXPENSE, "100", food, on=date(2026, 5, 15), account_id=bank.id)  # counted
    add(TransactionType.EXPENSE, "999", food, on=date(2026, 5, 16), account_id=bank.id)  # after day 15
    add(TransactionType.EXPENSE, "150", food, on=date(2026, 6, 3), account_id=bank.id)

    overview = dashboard.overview()

    assert (overview.previous_period.start, overview.previous_period.end) == (
        date(2026, 5, 1), date(2026, 5, 15)
    )
    assert overview.previous_period_expenses == Money.of("100")
    assert overview.health.spending_change == Decimal("0.5000")
    assert overview.health.spending_level is HealthLevel.POOR


def test_monthly_flows(
    dashboard: DashboardService, bank: Account, salary: Category, food: Category,
    add: AddTransaction,
) -> None:
    add(TransactionType.INCOME, "5000", salary, on=date(2026, 1, 31), account_id=bank.id)
    add(TransactionType.INCOME, "6000", salary, on=date(2026, 4, 1), account_id=bank.id)
    add(TransactionType.EXPENSE, "1000.10", food, on=date(2026, 4, 30), account_id=bank.id)
    add(TransactionType.EXPENSE, "20", food, on=TODAY, account_id=bank.id)

    flows = dashboard.overview().monthly_flows

    assert [f.month for f in flows] == [date(2026, m, 1) for m in range(1, 7)]
    by_month = {f.month.month: (f.income, f.expenses) for f in flows}
    assert by_month[1] == (Money.of("5000"), Money.zero())
    assert by_month[4] == (Money.of("6000"), Money.of("1000.10"))
    assert by_month[6] == (Money.zero(), Money.of("20"))
    assert flows[3].net == Money.of("4999.90")


def _record(transactions: TransactionService, account: Account, type_: TransactionType,
            amount: str, category: Category, on: date) -> None:
    """Record without the ``add`` fixture, which creates an extra account."""
    transactions.create(TransactionDraft(account.id, type_, amount, on, category.id))


def test_balance_history_matches_balance_service_every_day(
    dashboard: DashboardService, balances: BalanceService, accounts: AccountService,
    transactions: TransactionService, salary: Category, food: Category,
) -> None:
    bank = accounts.create("Bank", opening_balance="1000", opening_date=date(2026, 2, 1))
    cash = accounts.create("Cash", opening_balance="250.50", opening_date=date(2026, 4, 10))
    _record(transactions, bank, TransactionType.INCOME, "3000", salary, date(2026, 2, 28))
    _record(transactions, cash, TransactionType.EXPENSE, "75.25", food, date(2026, 4, 10))
    _record(transactions, bank, TransactionType.EXPENSE, "10", food, TODAY)

    history = dashboard.overview().balance_history

    assert history[0].day == date(2026, 2, 1)  # starts at the first opening
    assert history[-1].day == TODAY
    assert len(history) == (TODAY - date(2026, 2, 1)).days + 1
    for point in history:
        assert point.balance == balances.total_balance(as_of=point.day), point.day


def test_balance_history_window_is_capped(
    dashboard: DashboardService, accounts: AccountService
) -> None:
    accounts.create("Old", opening_balance="5", opening_date=date(2020, 1, 1))

    history = dashboard.overview().balance_history

    assert len(history) == HISTORY_DAYS
    assert history[0].day == TODAY - timedelta(days=HISTORY_DAYS - 1)
    assert all(point.balance == Money.of("5") for point in history)


def test_spending_by_category_top_five_plus_other(
    dashboard: DashboardService, bank: Account, categories: CategoryService, add: AddTransaction
) -> None:
    amounts = ["700", "600", "500", "400", "300", "200", "100"]
    for index, amount in enumerate(amounts):
        category = categories.create(f"C{index}", CategoryKind.EXPENSE)
        add(TransactionType.EXPENSE, amount, category, on=JUNE_1, account_id=bank.id)
    old = categories.create("Last month", CategoryKind.EXPENSE)
    add(TransactionType.EXPENSE, "9999", old, on=date(2026, 5, 31), account_id=bank.id)

    rows = dashboard.overview().spending_by_category

    assert [r.name for r in rows] == ["C0", "C1", "C2", "C3", "C4", OTHER_CATEGORY_LABEL]
    assert rows[-1].category_id is None and rows[-1].amount == Money.of("300")
    assert sum_money(r.amount for r in rows) == Money.of("2800")
    assert rows[0].share == Decimal("0.2500")


def test_allocation_slices_add_up_to_total_balance(
    dashboard: DashboardService, bank: Account, allocations: AllocationService
) -> None:
    allocations.create("Investments", initial_amount="5000")
    allocations.create("Savings", initial_amount="8000")

    overview = dashboard.overview()

    assert [s.name for s in overview.allocation_slices] == ["Savings", "Investments", "Available"]
    assert overview.allocation_slices[-1].amount == Money.of("16920")
    assert sum_money(s.amount for s in overview.allocation_slices) == overview.total_balance
    assert overview.health.allocated_share == Decimal("0.4345")  # 13,000 / 29,920
    assert overview.allocation.available == allocations.available()


def test_over_allocation_is_visible(
    dashboard: DashboardService, bank: Account, allocations: AllocationService, food: Category,
    add: AddTransaction,
) -> None:
    allocations.create("Savings", initial_amount="29920")
    add(TransactionType.EXPENSE, "20", food, on=TODAY, account_id=bank.id)

    overview = dashboard.overview()

    assert overview.allocation.is_over_allocated
    assert overview.allocation_slices[-1].amount == Money.of("-20")


def test_archived_allocations_with_no_money_are_hidden(
    dashboard: DashboardService, bank: Account, allocations: AllocationService,
    transfers: AllocationTransferService,
) -> None:
    travel = allocations.create("Travel", initial_amount="10")
    allocations.archive(travel.id)

    assert [s.name for s in dashboard.overview().allocation_slices] == ["Available"]


def test_runway_uses_last_three_complete_tracked_months(
    dashboard: DashboardService, accounts: AccountService, transactions: TransactionService,
    food: Category,
) -> None:
    bank = accounts.create("Bank", opening_balance="9000", opening_date=date(2026, 4, 1))
    _record(transactions, bank, TransactionType.EXPENSE, "1000", food, date(2026, 4, 5))
    _record(transactions, bank, TransactionType.EXPENSE, "2000", food, date(2026, 5, 5))
    _record(transactions, bank, TransactionType.EXPENSE, "5000", food, TODAY)  # current month

    overview = dashboard.overview()

    # Only April and May are tracked complete months: average 1,500; balance 1,000.
    assert overview.total_balance == Money.of("1000")
    assert overview.health.runway_months == Decimal("0.7")
    assert overview.health.runway_level is HealthLevel.POOR


def test_runway_unknown_in_first_month(
    dashboard: DashboardService, accounts: AccountService
) -> None:
    accounts.create("Bank", opening_balance="100", opening_date=JUNE_1)

    assert dashboard.overview().health.runway_months is None


def test_recent_transactions_are_newest_first(
    dashboard: DashboardService, bank: Account, food: Category, add: AddTransaction
) -> None:
    created = [
        add(TransactionType.EXPENSE, "1", food, on=date(2026, 3, day), account_id=bank.id)
        for day in range(1, 11)
    ]

    recent = dashboard.overview().recent_transactions

    assert [t.id for t in recent] == [t.id for t in reversed(created)][:8]


def test_names_for_display(
    dashboard: DashboardService, bank: Account, food: Category, add: AddTransaction
) -> None:
    add(TransactionType.EXPENSE, "1", food, account_id=bank.id)

    assert dashboard.overview().category_names[food.id] == "Food"


def test_mixed_currencies_are_rejected(
    dashboard: DashboardService, accounts: AccountService
) -> None:
    accounts.create("Euro account", currency="EUR")

    with pytest.raises(CurrencyMismatchError):
        dashboard.overview()


def test_query_count_does_not_grow_with_data(
    dashboard: DashboardService, database: Database, bank: Account, food: Category,
    categories: CategoryService, allocations: AllocationService, add: AddTransaction,
) -> None:
    def count_queries() -> int:
        statements: list[str] = []
        listener = lambda *args: statements.append(args[2])  # noqa: E731
        event.listen(database.engine, "before_cursor_execute", listener)
        try:
            dashboard.overview()
        finally:
            event.remove(database.engine, "before_cursor_execute", listener)
        return len(statements)

    small = count_queries()
    for index in range(30):
        category = categories.create(f"Cat {index}", CategoryKind.EXPENSE)
        add(TransactionType.EXPENSE, "1", category, on=date(2026, 3, 1 + index % 28),
            account_id=bank.id)
    allocations.create("Savings", initial_amount="10")

    assert count_queries() == small
    assert small <= 12


def test_matches_transaction_service_totals(
    dashboard: DashboardService, transactions: TransactionService, bank: Account,
    salary: Category, food: Category, add: AddTransaction,
) -> None:
    add(TransactionType.INCOME, "1234.56", salary, on=date(2026, 6, 2), account_id=bank.id)
    add(TransactionType.EXPENSE, "0.07", food, on=date(2026, 6, 3), account_id=bank.id)
    add(TransactionType.EXPENSE, "5", food, on=date(2026, 5, 31), account_id=bank.id)

    overview = dashboard.overview()
    page = transactions.search(TransactionQuery(filters=TransactionFilter(start=JUNE_1, end=TODAY)))

    assert (overview.income, overview.expenses) == (page.income, page.expenses)
