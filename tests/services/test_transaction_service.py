from dataclasses import replace
from datetime import date, datetime

import pytest

from money_manager.core.errors import NotFoundError, ValidationError
from money_manager.domain.entities import Account, Category, TransactionDraft, TransactionFilter
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.money import Money
from money_manager.services import AccountService, CategoryService, TransactionService
from tests.services.support import OPENING_DATE, TODAY, AddTransaction


def _draft(account: Account, category: Category | None, **overrides: object) -> TransactionDraft:
    draft = TransactionDraft(
        account_id=account.id,
        type=TransactionType.EXPENSE,
        amount="300",
        occurred_on=TODAY,
        category_id=None if category is None else category.id,
    )
    return replace(draft, **overrides)  # type: ignore[arg-type]


class TestCreate:
    def test_income(self, add: AddTransaction, salary: Category) -> None:
        tx = add(TransactionType.INCOME, "12000", salary, description="June salary")

        assert tx.type is TransactionType.INCOME
        assert tx.amount == Money.of("12000")
        assert tx.signed_amount == Money.of("12000")
        assert tx.category_id == salary.id
        assert tx.description == "June salary"

    def test_expense_is_stored_positive_with_negative_effect(
        self, add: AddTransaction, food: Category
    ) -> None:
        tx = add(TransactionType.EXPENSE, "300.50", food)

        assert tx.amount == Money.of("300.50")
        assert tx.signed_amount == Money.of("-300.50")

    def test_adjustments(self, add: AddTransaction) -> None:
        assert add(TransactionType.ADJUSTMENT_IN, "10").signed_amount == Money.of("10")
        assert add(TransactionType.ADJUSTMENT_OUT, "4").signed_amount == Money.of("-4")

    def test_round_trips_through_database(
        self, add: AddTransaction, transactions: TransactionService, food: Category
    ) -> None:
        created = add(TransactionType.EXPENSE, "0.01", food, notes="  tip  ")

        loaded = transactions.get(created.id)

        assert loaded == created
        assert loaded.amount.amount.as_tuple().exponent == -2
        assert loaded.notes == "tip"


class TestInvalid:
    @pytest.mark.parametrize(
        ("overrides", "field"),
        [
            ({"amount": "0"}, "amount"),
            ({"amount": "-300"}, "amount"),
            ({"amount": 300.0}, "amount"),
            ({"amount": "12.345"}, "amount"),
            ({"amount": "lots"}, "amount"),
            ({"type": "transfer"}, "type"),
            ({"occurred_on": date(2026, 6, 16)}, "occurred_on"),
            ({"occurred_on": date(2025, 12, 31)}, "occurred_on"),
            ({"occurred_on": datetime(2026, 6, 1, 9, 30)}, "occurred_on"),
            ({"occurred_on": "2026-06-01"}, "occurred_on"),
            ({"category_id": 9999}, "category_id"),
            ({"category_id": None}, "category_id"),
            ({"category_id": "1"}, "category_id"),
            ({"account_id": 9999}, "account_id"),
            ({"account_id": 0}, "account_id"),
            ({"description": "x" * 201}, "description"),
        ],
    )
    def test_rejected_and_nothing_saved(
        self,
        transactions: TransactionService,
        account: Account,
        food: Category,
        overrides: dict[str, object],
        field: str,
    ) -> None:
        with pytest.raises(ValidationError) as info:
            transactions.create(_draft(account, food, **overrides))

        assert info.value.field == field
        assert transactions.list() == []

    def test_expense_with_income_category(
        self, transactions: TransactionService, account: Account, salary: Category
    ) -> None:
        with pytest.raises(ValidationError, match="income category"):
            transactions.create(_draft(account, salary))

    def test_income_with_expense_category(
        self, transactions: TransactionService, account: Account, food: Category
    ) -> None:
        with pytest.raises(ValidationError, match="expense category"):
            transactions.create(_draft(account, food, type=TransactionType.INCOME))

    def test_adjustment_with_category(
        self, transactions: TransactionService, account: Account, food: Category
    ) -> None:
        with pytest.raises(ValidationError, match="do not use a category"):
            transactions.create(_draft(account, food, type=TransactionType.ADJUSTMENT_IN))

    def test_archived_category(
        self,
        transactions: TransactionService,
        categories: CategoryService,
        account: Account,
        food: Category,
    ) -> None:
        categories.archive(food.id)

        with pytest.raises(ValidationError, match="archived"):
            transactions.create(_draft(account, food))


class TestReadAndFilter:
    def test_list_is_newest_first(
        self, transactions: TransactionService, add: AddTransaction, food: Category
    ) -> None:
        older = add(TransactionType.EXPENSE, "1", food, on=date(2026, 2, 1))
        newer = add(TransactionType.EXPENSE, "2", food, on=date(2026, 5, 1))
        same_day_later = add(TransactionType.EXPENSE, "3", food, on=date(2026, 5, 1))

        assert [t.id for t in transactions.list()] == [same_day_later.id, newer.id, older.id]

    def test_filters(
        self,
        transactions: TransactionService,
        accounts: AccountService,
        add: AddTransaction,
        food: Category,
        salary: Category,
    ) -> None:
        other = accounts.create("Other", opening_date=OPENING_DATE)
        salary_tx = add(TransactionType.INCOME, "100", salary, on=date(2026, 3, 1))
        food_tx = add(TransactionType.EXPENSE, "10", food, on=date(2026, 4, 1))
        adjustment = add(TransactionType.ADJUSTMENT_IN, "1", on=date(2026, 5, 1))
        other_tx = add(TransactionType.EXPENSE, "5", food, on=date(2026, 5, 2), account_id=other.id)

        def ids(**criteria: object) -> list[int]:
            return [t.id for t in transactions.list(TransactionFilter(**criteria))]  # type: ignore[arg-type]

        assert ids() == [other_tx.id, adjustment.id, food_tx.id, salary_tx.id]
        assert ids(account_id=other.id) == [other_tx.id]
        assert ids(category_id=food.id) == [other_tx.id, food_tx.id]
        assert ids(types=frozenset({TransactionType.INCOME})) == [salary_tx.id]
        assert ids(start=date(2026, 4, 1), end=date(2026, 5, 1)) == [adjustment.id, food_tx.id]

    def test_get_unknown(self, transactions: TransactionService) -> None:
        with pytest.raises(NotFoundError):
            transactions.get(12345)


class TestUpdate:
    def test_replaces_all_fields(
        self,
        transactions: TransactionService,
        add: AddTransaction,
        account: Account,
        food: Category,
        salary: Category,
    ) -> None:
        tx = add(TransactionType.EXPENSE, "300", food, description="Lunch")

        updated = transactions.update(
            tx.id,
            _draft(
                account, salary, type=TransactionType.INCOME, amount="450.75",
                occurred_on=date(2026, 6, 10), description="Refund", notes="n",
            ),
        )

        assert updated.id == tx.id
        assert (updated.type, updated.amount, updated.category_id) == (
            TransactionType.INCOME, Money.of("450.75"), salary.id
        )
        assert (updated.occurred_on, updated.description, updated.notes) == (
            date(2026, 6, 10), "Refund", "n"
        )
        assert transactions.get(tx.id) == updated

    def test_invalid_update_leaves_original_untouched(
        self, transactions: TransactionService, add: AddTransaction, account: Account,
        food: Category,
    ) -> None:
        tx = add(TransactionType.EXPENSE, "300", food)

        with pytest.raises(ValidationError):
            transactions.update(tx.id, _draft(account, food, amount="0"))

        assert transactions.get(tx.id) == tx

    def test_can_keep_archived_category(
        self,
        transactions: TransactionService,
        categories: CategoryService,
        add: AddTransaction,
        account: Account,
        food: Category,
    ) -> None:
        tx = add(TransactionType.EXPENSE, "300", food)
        categories.archive(food.id)

        updated = transactions.update(tx.id, _draft(account, food, amount="350"))

        assert updated.amount == Money.of("350")

    def test_cannot_switch_to_other_archived_category(
        self,
        transactions: TransactionService,
        categories: CategoryService,
        add: AddTransaction,
        account: Account,
        food: Category,
    ) -> None:
        tx = add(TransactionType.EXPENSE, "300", food)
        rent = categories.create("Rent", CategoryKind.EXPENSE)
        categories.archive(rent.id)

        with pytest.raises(ValidationError, match="archived"):
            transactions.update(tx.id, _draft(account, rent))

    def test_unknown_transaction(
        self, transactions: TransactionService, account: Account, food: Category
    ) -> None:
        with pytest.raises(NotFoundError):
            transactions.update(999, _draft(account, food))


class TestDelete:
    def test_delete(self, transactions: TransactionService, add: AddTransaction, food: Category) -> None:
        keep = add(TransactionType.EXPENSE, "1", food)
        remove = add(TransactionType.EXPENSE, "2", food)

        transactions.delete(remove.id)

        assert transactions.list() == [keep]
        with pytest.raises(NotFoundError):
            transactions.get(remove.id)

    def test_delete_unknown(self, transactions: TransactionService) -> None:
        with pytest.raises(NotFoundError):
            transactions.delete(999)
