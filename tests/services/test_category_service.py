import pytest

from money_manager.core.errors import ConflictError, NotFoundError, ValidationError
from money_manager.domain.entities import Account, Category
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.services import CategoryService
from tests.services.support import AddTransaction

USER_EXPENSES = ["Food", "Transport", "Gaming", "Rent", "Investment", "Subscriptions",
                 "Travel", "Shopping"]
USER_INCOME = ["Salary", "Freelance"]


def test_fresh_database_has_no_categories(categories: CategoryService) -> None:
    assert categories.list(include_archived=True) == []


def test_user_can_create_any_categories(categories: CategoryService) -> None:
    for name in USER_EXPENSES:
        categories.create(name, CategoryKind.EXPENSE)
    for name in USER_INCOME:
        categories.create(name, "income")

    assert sorted(c.name for c in categories.list(CategoryKind.EXPENSE)) == sorted(USER_EXPENSES)
    assert sorted(c.name for c in categories.list("income")) == sorted(USER_INCOME)
    assert len(categories.list()) == len(USER_EXPENSES) + len(USER_INCOME)


def test_names_are_cleaned(categories: CategoryService) -> None:
    assert categories.create("  Eating   out ", CategoryKind.EXPENSE).name == "Eating out"


def test_duplicate_within_kind_is_rejected(categories: CategoryService) -> None:
    categories.create("Food", CategoryKind.EXPENSE)

    with pytest.raises(ConflictError):
        categories.create("FOOD", CategoryKind.EXPENSE)


def test_same_name_allowed_for_different_kinds(categories: CategoryService) -> None:
    categories.create("Investment", CategoryKind.EXPENSE)

    income = categories.create("Investment", CategoryKind.INCOME)

    assert income.kind is CategoryKind.INCOME


@pytest.mark.parametrize(("name", "kind"), [("", "expense"), ("Food", "savings"), ("x" * 41, "income")])
def test_invalid_input(categories: CategoryService, name: str, kind: str) -> None:
    with pytest.raises(ValidationError):
        categories.create(name, kind)


def test_rename(categories: CategoryService, food: Category) -> None:
    renamed = categories.rename(food.id, "Groceries")

    assert renamed.name == "Groceries"
    assert categories.get(food.id).name == "Groceries"


def test_rename_conflict(categories: CategoryService, food: Category) -> None:
    categories.create("Rent", CategoryKind.EXPENSE)

    with pytest.raises(ConflictError):
        categories.rename(food.id, "rent")


def test_archive_and_restore(categories: CategoryService, food: Category) -> None:
    archived = categories.archive(food.id)

    assert archived.is_archived
    assert categories.list() == []
    assert categories.list(include_archived=True) == [archived]
    assert not categories.restore(food.id).is_archived


def test_delete_unused_category(categories: CategoryService, food: Category) -> None:
    categories.delete(food.id)

    with pytest.raises(NotFoundError):
        categories.get(food.id)


def test_cannot_delete_used_category(
    categories: CategoryService, account: Account, food: Category, add: AddTransaction
) -> None:
    add(TransactionType.EXPENSE, "5", food)

    with pytest.raises(ConflictError, match="archive"):
        categories.delete(food.id)


def test_unknown_category(categories: CategoryService) -> None:
    with pytest.raises(NotFoundError):
        categories.get(404)
    with pytest.raises(NotFoundError):
        categories.rename(404, "x")


class TestInvestmentFlag:
    def test_mark_expense_category(self, categories: CategoryService) -> None:
        stocks = categories.create("Stocks", CategoryKind.EXPENSE)

        assert categories.set_investment(stocks.id, True).is_investment
        assert categories.get(stocks.id).is_investment
        assert not categories.set_investment(stocks.id, False).is_investment

    def test_new_categories_are_not_investments(self, categories: CategoryService) -> None:
        assert not categories.create("Food", CategoryKind.EXPENSE).is_investment

    def test_income_categories_cannot_be_investments(self, categories: CategoryService) -> None:
        salary = categories.create("Salary", CategoryKind.INCOME)

        with pytest.raises(ValidationError, match="expense"):
            categories.set_investment(salary.id, True)
        assert not categories.set_investment(salary.id, False).is_investment

    def test_flag_must_be_boolean(self, categories: CategoryService) -> None:
        stocks = categories.create("Stocks", CategoryKind.EXPENSE)
        with pytest.raises(ValidationError):
            categories.set_investment(stocks.id, "yes")  # type: ignore[arg-type]
        with pytest.raises(NotFoundError):
            categories.set_investment(404, True)
