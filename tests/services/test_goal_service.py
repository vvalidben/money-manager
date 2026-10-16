"""Goals on a real database, including their interaction with allocations."""

from datetime import date
from decimal import Decimal

import pytest

from money_manager.core.errors import (
    ConflictError,
    InsufficientFundsError,
    NotFoundError,
    ValidationError,
)
from money_manager.domain.entities import Account, Category, TransactionDraft
from money_manager.domain.enums import TransactionType
from money_manager.domain.goals import GoalStatus
from money_manager.domain.money import Money
from money_manager.persistence.database import Database
from money_manager.services import (
    AccountService,
    AllocationService,
    AllocationTransferService,
    BalanceService,
    GoalService,
    TransactionService,
)
from tests.services.support import OPENING_DATE, TODAY, fixed_today


@pytest.fixture
def goals(database: Database) -> GoalService:
    return GoalService(database, today=fixed_today)


@pytest.fixture
def bank(accounts: AccountService) -> Account:
    return accounts.create("Bank", opening_balance="30000", opening_date=OPENING_DATE)


class TestCreate:
    def test_backed_by_new_allocation_with_initial_money(
        self, goals: GoalService, allocations: AllocationService, balances: BalanceService,
        bank: Account,
    ) -> None:
        item = goals.create_with_new_allocation(
            "Emergency Fund", target="20000", initial_amount="12500",
            deadline=date(2026, 12, 31), description="Six months of rent",
        )

        assert item.current == Money.of("12500")
        assert item.progress == Decimal("0.6250")  # 62.5 %
        assert item.allocation_name == "Emergency Fund"
        assert item.goal.start_date == TODAY
        assert allocations.available() == Money.of("17500")
        assert balances.total_balance() == Money.of("30000")  # money only reorganised

    def test_initial_money_must_be_available(
        self, goals: GoalService, allocations: AllocationService, bank: Account
    ) -> None:
        with pytest.raises(InsufficientFundsError):
            goals.create_with_new_allocation("Car", target="50000", initial_amount="30000.01")

        assert goals.list() == []
        assert allocations.list(include_archived=True) == []  # rolled back together

    def test_backed_by_existing_allocation(
        self, goals: GoalService, allocations: AllocationService, bank: Account
    ) -> None:
        savings = allocations.create("Savings", initial_amount="8000")

        item = goals.create_with_allocation("House", target="100000", allocation_id=savings.id)

        assert item.current == Money.of("8000")
        assert item.progress == Decimal("0.0800")

    def test_an_allocation_backs_only_one_goal(
        self, goals: GoalService, allocations: AllocationService, bank: Account
    ) -> None:
        savings = allocations.create("Savings", initial_amount="8000")
        goals.create_with_allocation("House", target="100000", allocation_id=savings.id)

        with pytest.raises(ConflictError, match="only one goal"):
            goals.create_with_allocation("Car", target="5000", allocation_id=savings.id)

        summary = goals.summary()
        assert summary.total_saved == Money.of("8000")  # not 16,000

    def test_manual(self, goals: GoalService, balances: BalanceService, bank: Account) -> None:
        item = goals.create_manual("Gift fund", target="3000", current="1000.50")

        assert item.goal.is_manual and item.current == Money.of("1000.50")
        assert item.progress == Decimal("0.3335")
        assert balances.total_balance() == Money.of("30000")  # not part of any balance

    @pytest.mark.parametrize(
        ("kwargs", "field"),
        [
            ({"target": "0"}, "target"),
            ({"target": "-5"}, "target"),
            ({"target": 10.5}, "target"),
            ({"target": "1.005"}, "target"),
            ({"deadline": date(2026, 6, 14)}, "deadline"),
            ({"current": "-1"}, "current"),
        ],
    )
    def test_invalid_input(
        self, goals: GoalService, kwargs: dict[str, object], field: str
    ) -> None:
        fields: dict[str, object] = {"target": "100"}
        fields.update(kwargs)
        with pytest.raises(ValidationError) as info:
            goals.create_manual("Goal", **fields)  # type: ignore[arg-type]
        assert info.value.field == field
        assert goals.list() == []

    def test_duplicate_names(self, goals: GoalService) -> None:
        goals.create_manual("Trip", target="100")
        with pytest.raises(ConflictError):
            goals.create_manual("  TRIP ", target="200")

    def test_new_allocation_name_must_be_free(
        self, goals: GoalService, allocations: AllocationService
    ) -> None:
        allocations.create("Travel")
        with pytest.raises(ConflictError, match="allocation named"):
            goals.create_with_new_allocation("travel", target="100")
        assert goals.list() == []

    def test_unknown_or_archived_allocation(
        self, goals: GoalService, allocations: AllocationService
    ) -> None:
        old = allocations.create("Old")
        allocations.archive(old.id)
        with pytest.raises(ValidationError, match="does not exist"):
            goals.create_with_allocation("A", target="1", allocation_id=999)
        with pytest.raises(ValidationError, match="archived"):
            goals.create_with_allocation("B", target="1", allocation_id=old.id)


class TestUpdate:
    def test_edit_fields(self, goals: GoalService) -> None:
        item = goals.create_manual("Trip", target="100", current="50")

        updated = goals.update(item.goal.id, name="Japan trip", target="200",
                               deadline=date(2027, 3, 1), description="Cherry blossoms")

        assert (updated.goal.name, updated.goal.target, updated.goal.deadline) == (
            "Japan trip", Money.of("200"), date(2027, 3, 1)
        )
        assert updated.progress == Decimal("0.2500")  # recalculated for the new target

    def test_edit_keeps_a_passed_deadline(self, goals: GoalService, database: Database) -> None:
        item = goals.create_manual("Trip", target="100", deadline=TODAY)
        later = GoalService(database, today=lambda: date(2026, 7, 1))

        updated = later.update(item.goal.id, name="Trip", target="150", deadline=TODAY,
                               description="")

        assert updated.status is GoalStatus.OVERDUE
        with pytest.raises(ValidationError, match="past"):
            later.update(item.goal.id, name="Trip", target="150", deadline=date(2026, 6, 20),
                         description="")

    def test_invalid_edit_changes_nothing(self, goals: GoalService) -> None:
        item = goals.create_manual("Trip", target="100")
        with pytest.raises(ValidationError):
            goals.update(item.goal.id, name="Trip", target="0", deadline=None, description="")
        assert goals.get(item.goal.id).goal.target == Money.of("100")

    def test_manual_amount(self, goals: GoalService) -> None:
        item = goals.create_manual("Trip", target="100")

        assert goals.set_manual_amount(item.goal.id, "75").progress == Decimal("0.7500")
        with pytest.raises(ValidationError):
            goals.set_manual_amount(item.goal.id, "-1")

    def test_backed_goal_has_no_manual_amount(self, goals: GoalService, bank: Account) -> None:
        item = goals.create_with_new_allocation("Car", target="100")
        with pytest.raises(ValidationError, match="allocation"):
            goals.set_manual_amount(item.goal.id, "50")


class TestContributions:
    def test_add_and_withdraw_move_money_between_available_and_the_goal(
        self, goals: GoalService, allocations: AllocationService, balances: BalanceService,
        transfers: AllocationTransferService, bank: Account,
    ) -> None:
        item = goals.create_with_new_allocation("Car", target="10000", initial_amount="1000")

        after_add = goals.contribute(item.goal.id, "2500")
        assert after_add.current == Money.of("3500")
        assert allocations.available() == Money.of("26500")

        after_withdraw = goals.withdraw(item.goal.id, "500")
        assert after_withdraw.current == Money.of("3000")
        assert allocations.available() == Money.of("27000")

        assert balances.total_balance() == Money.of("30000")  # never changes
        assert [t.note for t in transfers.list()][:2] == [
            "Goal withdrawal: Car", "Goal contribution: Car"
        ]

    def test_cannot_add_more_than_available(
        self, goals: GoalService, bank: Account
    ) -> None:
        item = goals.create_with_new_allocation("Car", target="100000")
        with pytest.raises(InsufficientFundsError):
            goals.contribute(item.goal.id, "30000.01")
        assert goals.get(item.goal.id).current == Money.zero()

    def test_cannot_withdraw_more_than_saved(self, goals: GoalService, bank: Account) -> None:
        item = goals.create_with_new_allocation("Car", target="100", initial_amount="40")
        with pytest.raises(InsufficientFundsError):
            goals.withdraw(item.goal.id, "40.01")

    def test_manual_contributions(self, goals: GoalService) -> None:
        item = goals.create_manual("Gift", target="100", current="10")

        assert goals.contribute(item.goal.id, "15.50").current == Money.of("25.50")
        assert goals.withdraw(item.goal.id, "25.50").current == Money.zero()
        with pytest.raises(ValidationError):
            goals.withdraw(item.goal.id, "0.01")

    @pytest.mark.parametrize("amount", ["0", "-5", 5.0, "1.001"])
    def test_invalid_amounts(self, goals: GoalService, amount: object) -> None:
        item = goals.create_manual("Gift", target="100")
        with pytest.raises(ValidationError):
            goals.contribute(item.goal.id, amount)  # type: ignore[arg-type]

    def test_spending_from_the_goal_allocation_reduces_progress(
        self, goals: GoalService, transactions: TransactionService, bank: Account,
        food: Category,
    ) -> None:
        item = goals.create_with_new_allocation("Trip", target="5000", initial_amount="4000")

        transactions.create(TransactionDraft(bank.id, TransactionType.EXPENSE, "1500", TODAY,
                                             food.id, allocation_id=item.goal.allocation_id))

        assert goals.get(item.goal.id).current == Money.of("2500")

    def test_reaching_the_target(self, goals: GoalService, bank: Account) -> None:
        item = goals.create_with_new_allocation("Phone", target="3000", initial_amount="2000")

        done = goals.contribute(item.goal.id, "1500")

        assert done.is_complete and done.status is GoalStatus.COMPLETED
        assert done.progress == Decimal("1.1667")


class TestDelete:
    def test_delete_keeps_the_money_allocated(
        self, goals: GoalService, allocations: AllocationService, bank: Account
    ) -> None:
        item = goals.create_with_new_allocation("Car", target="100", initial_amount="60")

        goals.delete(item.goal.id)

        assert goals.list() == []
        assert allocations.balance(item.goal.allocation_id) == Money.of("60")
        assert allocations.available() == Money.of("29940")

    def test_delete_and_release_money(
        self, goals: GoalService, allocations: AllocationService, balances: BalanceService,
        bank: Account,
    ) -> None:
        item = goals.create_with_new_allocation("Car", target="100", initial_amount="60")

        goals.delete(item.goal.id, release_money=True)

        assert allocations.get(item.goal.allocation_id).is_archived
        assert allocations.available() == Money.of("30000")
        assert balances.total_balance() == Money.of("30000")
        assert allocations.check_consistency().is_consistent

    def test_delete_manual(self, goals: GoalService) -> None:
        item = goals.create_manual("Gift", target="100", current="5")
        goals.delete(item.goal.id, release_money=True)
        with pytest.raises(NotFoundError):
            goals.get(item.goal.id)

    def test_goal_allocation_cannot_be_archived_or_deleted_directly(
        self, goals: GoalService, allocations: AllocationService, bank: Account
    ) -> None:
        item = goals.create_with_new_allocation("Car", target="100")
        assert item.goal.allocation_id is not None

        with pytest.raises(ConflictError, match="goal"):
            allocations.archive(item.goal.allocation_id)
        with pytest.raises(ConflictError, match="goal"):
            allocations.delete(item.goal.allocation_id)

    def test_unknown_goal(self, goals: GoalService) -> None:
        for call in (goals.get, goals.delete):
            with pytest.raises(NotFoundError):
                call(404)
        with pytest.raises(NotFoundError):
            goals.contribute(404, "1")


def test_summary_and_order(goals: GoalService, bank: Account) -> None:
    goals.create_with_new_allocation("Emergency Fund", target="20000", initial_amount="12500",
                                     deadline=date(2026, 12, 31))
    goals.create_manual("Trip", target="5000", current="5000")
    goals.create_manual("Laptop", target="12000", deadline=date(2026, 9, 1))

    summary = goals.summary()

    assert [g.goal.name for g in summary.goals] == ["Laptop", "Emergency Fund", "Trip"]
    assert summary.total_target == Money.of("37000")
    assert summary.total_saved == Money.of("17500")
    assert summary.overall_progress == Decimal("0.4730")
    assert summary.completed_count == 1
    assert summary.required_per_month.is_positive()
