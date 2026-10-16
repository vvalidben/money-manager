from datetime import date

import pytest

from money_manager.core.errors import NotFoundError, ValidationError
from money_manager.domain.entities import Account, Category, TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.money import MAX_ABS_AMOUNT, Money
from money_manager.persistence.database import Database
from money_manager.services import (
    AccountService,
    BalanceService,
    CategoryService,
    TransactionService,
)
from tests.services.support import OPENING_DATE, TODAY, AddTransaction, fixed_today


def test_new_account_balance_is_opening_balance(
    accounts: AccountService, balances: BalanceService
) -> None:
    account = accounts.create("Bank", opening_balance="30000", opening_date=OPENING_DATE)

    assert balances.balance(account.id) == Money.of("30000")


def test_example_from_requirements(
    balances: BalanceService, categories: CategoryService, account: Account,
    salary: Category, food: Category, add: AddTransaction,
) -> None:
    investment = categories.create("Investment", CategoryKind.EXPENSE)
    subscriptions = categories.create("Subscriptions", CategoryKind.EXPENSE)

    add(TransactionType.INCOME, "12000", salary)
    add(TransactionType.EXPENSE, "300", food)
    add(TransactionType.EXPENSE, "2000", investment)
    add(TransactionType.EXPENSE, "200", subscriptions)

    assert balances.balance(account.id) == Money.of("9500")


def test_breakdown_follows_formula(
    accounts: AccountService, balances: BalanceService, salary: Category, food: Category,
    add: AddTransaction,
) -> None:
    account = accounts.create("Bank", opening_balance="1000", opening_date=OPENING_DATE)
    add(TransactionType.INCOME, "12000", salary, account_id=account.id)
    add(TransactionType.INCOME, "500.50", salary, account_id=account.id)
    add(TransactionType.EXPENSE, "300.25", food, account_id=account.id)
    add(TransactionType.ADJUSTMENT_IN, "20", account_id=account.id)
    add(TransactionType.ADJUSTMENT_OUT, "5.10", account_id=account.id)

    breakdown = balances.breakdown(account.id)

    assert breakdown.opening_balance == Money.of("1000")
    assert breakdown.income == Money.of("12500.50")
    assert breakdown.expenses == Money.of("300.25")
    assert breakdown.adjustments_in == Money.of("20")
    assert breakdown.adjustments_out == Money.of("5.10")
    # 1000 + 12500.50 − 300.25 + 20 − 5.10
    assert breakdown.balance == Money.of("13215.15")


def test_balance_can_become_negative(
    balances: BalanceService, account: Account, food: Category, add: AddTransaction
) -> None:
    add(TransactionType.EXPENSE, "75.30", food)

    assert balances.balance(account.id) == Money.of("-75.30")


class TestRecalculation:
    def test_after_edit(
        self, balances: BalanceService, transactions: TransactionService, account: Account,
        food: Category, add: AddTransaction,
    ) -> None:
        tx = add(TransactionType.EXPENSE, "300", food)
        assert balances.balance(account.id) == Money.of("-300")

        transactions.update(
            tx.id,
            TransactionDraft(account.id, TransactionType.EXPENSE, "120.40", TODAY, food.id),
        )

        assert balances.balance(account.id) == Money.of("-120.40")

    def test_after_changing_type_flips_direction(
        self, balances: BalanceService, transactions: TransactionService, account: Account,
        food: Category, salary: Category, add: AddTransaction,
    ) -> None:
        tx = add(TransactionType.EXPENSE, "100", food)

        transactions.update(
            tx.id, TransactionDraft(account.id, TransactionType.INCOME, "100", TODAY, salary.id)
        )

        assert balances.balance(account.id) == Money.of("100")

    def test_after_moving_to_other_account(
        self, balances: BalanceService, transactions: TransactionService,
        accounts: AccountService, account: Account, food: Category, add: AddTransaction,
    ) -> None:
        other = accounts.create("Other", opening_date=OPENING_DATE)
        tx = add(TransactionType.EXPENSE, "40", food)

        transactions.update(
            tx.id, TransactionDraft(other.id, TransactionType.EXPENSE, "40", TODAY, food.id)
        )

        assert balances.balance(account.id) == Money.zero()
        assert balances.balance(other.id) == Money.of("-40")
        assert balances.total_balance() == Money.of("-40")

    def test_after_delete(
        self, balances: BalanceService, transactions: TransactionService, account: Account,
        salary: Category, food: Category, add: AddTransaction,
    ) -> None:
        add(TransactionType.INCOME, "1000", salary)
        expense = add(TransactionType.EXPENSE, "250", food)
        assert balances.balance(account.id) == Money.of("750")

        transactions.delete(expense.id)

        assert balances.balance(account.id) == Money.of("1000")

    def test_after_changing_opening_balance(
        self, balances: BalanceService, accounts: AccountService, account: Account,
        food: Category, add: AddTransaction,
    ) -> None:
        add(TransactionType.EXPENSE, "250", food)

        accounts.update(account.id, name="Main", opening_balance="5000", opening_date=OPENING_DATE)

        assert balances.balance(account.id) == Money.of("4750")


class TestPrecision:
    def test_cents_add_up_exactly(
        self, balances: BalanceService, account: Account, salary: Category, food: Category,
        add: AddTransaction,
    ) -> None:
        for _ in range(3):
            add(TransactionType.INCOME, "0.10", salary)
        add(TransactionType.EXPENSE, "0.30", food)

        assert balances.balance(account.id) == Money.zero()

    def test_many_transactions(
        self, balances: BalanceService, account: Account, salary: Category, add: AddTransaction
    ) -> None:
        for _ in range(200):
            add(TransactionType.INCOME, "0.01", salary)

        assert balances.balance(account.id) == Money.of("2.00")

    def test_largest_amounts(
        self, accounts: AccountService, balances: BalanceService, salary: Category,
        food: Category, add: AddTransaction,
    ) -> None:
        account = accounts.create(
            "Big", opening_balance=MAX_ABS_AMOUNT, opening_date=OPENING_DATE
        )
        add(TransactionType.EXPENSE, MAX_ABS_AMOUNT, food, account_id=account.id)
        add(TransactionType.INCOME, "0.01", salary, account_id=account.id)

        assert balances.balance(account.id) == Money.of("0.01")

    def test_survives_reopening_the_database(
        self, database: Database, balances: BalanceService, account: Account,
        salary: Category, food: Category, add: AddTransaction,
    ) -> None:
        add(TransactionType.INCOME, "12345.67", salary)
        add(TransactionType.EXPENSE, "0.99", food)
        database.dispose()

        reopened = Database(str(database.engine.url))
        try:
            fresh = BalanceService(reopened, TransactionService(reopened, today=fixed_today))
            assert fresh.balance(account.id) == Money.of("12344.68")
        finally:
            reopened.dispose()


class TestHistorical:
    def test_as_of_excludes_later_transactions(
        self, balances: BalanceService, account: Account, salary: Category, food: Category,
        add: AddTransaction,
    ) -> None:
        add(TransactionType.INCOME, "1000", salary, on=date(2026, 2, 1))
        add(TransactionType.EXPENSE, "100", food, on=date(2026, 3, 1))
        add(TransactionType.EXPENSE, "50", food, on=date(2026, 3, 2))

        assert balances.balance(account.id, as_of=date(2026, 1, 31)) == Money.zero()
        assert balances.balance(account.id, as_of=date(2026, 3, 1)) == Money.of("900")
        assert balances.balance(account.id, as_of=TODAY) == Money.of("850")

    def test_opening_day_is_valid(self, balances: BalanceService, account: Account) -> None:
        assert balances.balance(account.id, as_of=OPENING_DATE) == Money.zero()

    def test_before_opening_date_is_rejected(
        self, balances: BalanceService, account: Account
    ) -> None:
        with pytest.raises(ValidationError, match="opening date"):
            balances.balance(account.id, as_of=date(2025, 12, 31))

    def test_unknown_account(self, balances: BalanceService) -> None:
        with pytest.raises(NotFoundError):
            balances.balance(999)


class TestTotalBalance:
    def test_no_accounts(self, balances: BalanceService) -> None:
        assert balances.total_balance() == Money.zero("MAD")

    def test_sums_accounts(
        self, accounts: AccountService, balances: BalanceService, food: Category,
        add: AddTransaction,
    ) -> None:
        bank = accounts.create("Bank", opening_balance="30000", opening_date=OPENING_DATE)
        cash = accounts.create("Cash", opening_balance="500", opening_date=date(2026, 5, 1))
        add(TransactionType.EXPENSE, "120", food, account_id=cash.id)

        assert balances.total_balance() == Money.of("30380")
        # Cash did not exist yet in April.
        assert balances.total_balance(as_of=date(2026, 4, 30)) == Money.of("30000")


class TestReconcile:
    def test_increase_records_positive_adjustment(
        self, balances: BalanceService, account: Account, salary: Category, add: AddTransaction
    ) -> None:
        add(TransactionType.INCOME, "1000", salary)

        correction = balances.reconcile(account.id, "1250.50")

        assert correction is not None
        assert correction.type is TransactionType.ADJUSTMENT_IN
        assert correction.amount == Money.of("250.50")
        assert correction.category_id is None
        assert correction.description == "Balance correction"
        assert balances.balance(account.id) == Money.of("1250.50")

    def test_decrease_records_negative_adjustment(
        self, balances: BalanceService, account: Account, salary: Category, add: AddTransaction
    ) -> None:
        add(TransactionType.INCOME, "1000", salary)

        correction = balances.reconcile(account.id, "-20")

        assert correction is not None
        assert correction.type is TransactionType.ADJUSTMENT_OUT
        assert correction.amount == Money.of("1020")
        assert balances.balance(account.id) == Money.of("-20")

    def test_no_change_needed(
        self, balances: BalanceService, transactions: TransactionService, account: Account
    ) -> None:
        assert balances.reconcile(account.id, "0.00") is None
        assert transactions.list() == []

    def test_on_past_date(
        self, balances: BalanceService, account: Account, food: Category, add: AddTransaction
    ) -> None:
        add(TransactionType.EXPENSE, "100", food, on=date(2026, 6, 1))

        correction = balances.reconcile(account.id, "500", on=date(2026, 3, 1))

        assert correction is not None and correction.occurred_on == date(2026, 3, 1)
        assert balances.balance(account.id, as_of=date(2026, 3, 1)) == Money.of("500")
        assert balances.balance(account.id) == Money.of("400")

    @pytest.mark.parametrize(
        ("target", "on"),
        [(12.5, None), ("1.001", None), ("100", date(2026, 6, 16)), ("100", date(2025, 1, 1))],
    )
    def test_invalid(
        self, balances: BalanceService, transactions: TransactionService, account: Account,
        target: object, on: date | None,
    ) -> None:
        with pytest.raises(ValidationError):
            balances.reconcile(account.id, target, on=on)  # type: ignore[arg-type]
        assert transactions.list() == []
