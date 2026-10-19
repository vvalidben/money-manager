"""Monthly budgets per expense category."""

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from money_manager.core.errors import NotFoundError, ValidationError
from money_manager.domain.budgets import Budget, BudgetLevel, BudgetStatus
from money_manager.domain.entities import Account, Category, TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.money import Money
from money_manager.domain.periods import month_start
from money_manager.services import AppServices
from money_manager.services.data_service import RESET_CONFIRMATION
from tests.services.support import fixed_today


@pytest.fixture
def bank(app_services: AppServices) -> Account:
    return app_services.accounts.create("Bank", opening_balance="10000",
                                        opening_date=date(2025, 1, 1))


@pytest.fixture
def food(app_services: AppServices) -> Category:
    return app_services.categories.create("Groceries", CategoryKind.EXPENSE)


def spend(services: AppServices, account: Account, category: Category, amount: str,
          on: date) -> None:
    services.transactions.create(TransactionDraft(account.id, TransactionType.EXPENSE, amount,
                                                  on, category.id))


def status(spent: str, limit: str = "1000", today: date = date(2026, 6, 15)) -> BudgetStatus:
    return BudgetStatus(Budget(1, 1, Money.of(limit)), "Groceries", Money.of(spent), today)


class TestRules:
    @pytest.mark.parametrize(("spent", "level"), [
        ("0", BudgetLevel.ON_TRACK), ("849.99", BudgetLevel.ON_TRACK),
        ("850", BudgetLevel.NEAR_LIMIT), ("1000", BudgetLevel.NEAR_LIMIT),
        ("1000.01", BudgetLevel.OVER),
    ])
    def test_levels(self, spent: str, level: BudgetLevel) -> None:
        assert status(spent).level is level

    def test_remaining_and_ratio_are_exact(self) -> None:
        over = status("1250.50")
        assert over.remaining == Money.of("-250.50")
        assert over.ratio == Decimal("1.2505")

    def test_projection_at_the_pace_so_far(self) -> None:
        assert status("300", today=date(2026, 6, 15)).projected == Money.of("600")  # 30 days
        assert status("300", today=date(2026, 6, 2)).projected is None  # too early
        assert status("300", today=date(2026, 6, 30)).projected is None  # month is over


class TestService:
    def test_only_this_months_spending_counts(self, app_services: AppServices, bank: Account,
                                              food: Category) -> None:
        app_services.budgets.set(food.id, "2000")
        start = month_start(fixed_today())
        spend(app_services, bank, food, "400", start)
        spend(app_services, bank, food, "55.30", fixed_today())
        spend(app_services, bank, food, "999", start - timedelta(days=1))  # last month

        [only] = app_services.budgets.overview().statuses
        assert only.spent == Money.of("455.30")
        assert only.remaining == Money.of("1544.70")
        assert only.category_name == "Groceries"

    def test_summary_totals_and_order(self, app_services: AppServices, bank: Account,
                                      food: Category) -> None:
        fun = app_services.categories.create("Dining", CategoryKind.EXPENSE)
        app_services.budgets.set(food.id, "2000")
        app_services.budgets.set(fun.id, "300")
        spend(app_services, bank, food, "100", fixed_today())
        spend(app_services, bank, fun, "450", fixed_today())

        summary = app_services.budgets.overview()
        assert [s.category_name for s in summary.statuses] == ["Dining", "Groceries"]
        assert (summary.planned, summary.spent) == (Money.of("2300"), Money.of("550"))
        assert summary.remaining == Money.of("1750") and summary.over_count == 1

    def test_setting_again_changes_the_limit(self, app_services: AppServices,
                                             food: Category) -> None:
        first = app_services.budgets.set(food.id, "2000")
        second = app_services.budgets.set(food.id, "2500.50")
        assert first.id == second.id and second.limit == Money.of("2500.50")

    @pytest.mark.parametrize("amount", ["0", "-10", "12.345", "abc"])
    def test_limits_must_be_positive_amounts(self, app_services: AppServices, food: Category,
                                             amount: str) -> None:
        with pytest.raises(ValidationError):
            app_services.budgets.set(food.id, amount)
        assert app_services.budgets.overview().statuses == ()

    def test_only_expense_categories(self, app_services: AppServices) -> None:
        salary = app_services.categories.create("Salary", CategoryKind.INCOME)
        with pytest.raises(ValidationError, match="expense categories"):
            app_services.budgets.set(salary.id, "100")
        with pytest.raises(ValidationError, match="does not exist"):
            app_services.budgets.set(999, "100")

    def test_remove(self, app_services: AppServices, food: Category) -> None:
        app_services.budgets.set(food.id, "100")
        app_services.budgets.remove(food.id)
        assert app_services.budgets.overview().statuses == ()
        with pytest.raises(NotFoundError):
            app_services.budgets.remove(food.id)

    def test_deleting_an_unused_category_removes_its_budget(self, app_services: AppServices,
                                                            food: Category) -> None:
        app_services.budgets.set(food.id, "100")
        app_services.categories.delete(food.id)
        assert app_services.budgets.overview().statuses == ()

    def test_backups_include_budgets(self, app_services: AppServices, food: Category,
                                     tmp_path: Path) -> None:
        app_services.budgets.set(food.id, "750")
        path = tmp_path / "backup.json"
        app_services.data.export_backup(path)
        app_services.data.reset(RESET_CONFIRMATION)
        app_services.data.import_backup(path)
        [restored] = app_services.budgets.overview().statuses
        assert restored.budget.limit == Money.of("750")
