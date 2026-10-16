"""Regression tests for the bugs fixed in the Sprint 15 quality pass."""

from datetime import date

import pytest

from money_manager.core.errors import NotFoundError, ValidationError
from money_manager.domain.entities import TransactionDraft, TransactionQuery
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.money import Money
from money_manager.domain.periods import DateRange
from money_manager.domain.validation import MAX_RECORD_ID, is_record_id, validate_id
from money_manager.services import AppServices
from tests.services.support import TODAY


@pytest.fixture
def archived_pot(app_services: AppServices) -> tuple[AppServices, int, int, int]:
    """An expense and an income tagged to an allocation that was then archived."""
    s = app_services
    bank = s.accounts.create("Bank", opening_balance="1000", opening_date=date(2026, 1, 1))
    food = s.categories.create("Food", CategoryKind.EXPENSE)
    salary = s.categories.create("Salary", CategoryKind.INCOME)
    pot = s.allocations.create("Holiday", initial_amount="300")
    expense = s.transactions.create(TransactionDraft(bank.id, TransactionType.EXPENSE, "100",
                                                     TODAY, food.id, allocation_id=pot.id))
    income = s.transactions.create(TransactionDraft(bank.id, TransactionType.INCOME, "50",
                                                    TODAY, salary.id, allocation_id=pot.id))
    s.allocations.archive(pot.id)  # returns its 250 to Available
    return s, pot.id, expense.id, income.id


class TestArchivedAllocationStaysEmpty:
    """Bug: deleting or editing an old expense tagged to an archived allocation put
    money back into it, leaving an archived allocation holding money."""

    def test_deleting_a_tagged_expense_is_refused(self, archived_pot) -> None:  # noqa: ANN001
        s, pot, expense, _ = archived_pot
        before = s.allocations.summary()
        with pytest.raises(ValidationError, match="archived") as info:
            s.transactions.delete(expense)
        assert info.value.field == "allocation_id"
        assert s.allocations.balance(pot) == Money.zero()
        assert s.allocations.summary() == before
        assert s.allocations.check_consistency().is_consistent

    def test_shrinking_a_tagged_expense_is_refused(self, archived_pot) -> None:  # noqa: ANN001
        s, _, expense, _ = archived_pot
        old = s.transactions.get(expense)
        draft = TransactionDraft(old.account_id, old.type, "10", old.occurred_on,
                                 old.category_id, allocation_id=old.allocation_id)
        with pytest.raises(ValidationError, match="archived"):
            s.transactions.update(expense, draft)

    def test_harmless_edits_still_work(self, archived_pot) -> None:  # noqa: ANN001
        s, pot, expense, _ = archived_pot
        old = s.transactions.get(expense)
        s.transactions.update(expense, TransactionDraft(
            old.account_id, old.type, "100", old.occurred_on, old.category_id,
            description="renamed", allocation_id=pot))
        assert s.transactions.get(expense).description == "renamed"

    def test_untagging_is_refused_too(self, archived_pot) -> None:  # noqa: ANN001
        s, _, expense, _ = archived_pot
        old = s.transactions.get(expense)
        # Moving it to Available would also refund the archived allocation.
        with pytest.raises(ValidationError, match="archived"):
            s.transactions.update(expense, TransactionDraft(
                old.account_id, old.type, "100", old.occurred_on, old.category_id))

    def test_after_restoring_the_allocation_the_delete_works(
        self, archived_pot,  # noqa: ANN001
    ) -> None:
        s, pot, expense, _ = archived_pot
        s.allocations.restore(pot)
        s.transactions.delete(expense)
        assert s.allocations.balance(pot) == Money.of("100")


class TestRecordIds:
    """Bug: ids beyond SQLite's 64-bit range crashed with OverflowError."""

    @pytest.mark.parametrize("value", [1, MAX_RECORD_ID])
    def test_valid(self, value: int) -> None:
        assert is_record_id(value) and validate_id(value, "x") == value

    @pytest.mark.parametrize("value", [0, -1, MAX_RECORD_ID + 1, -(2**70), True, "1", 1.0, None])
    def test_invalid(self, value: object) -> None:
        assert not is_record_id(value)
        with pytest.raises(ValidationError):
            validate_id(value, "x")

    def test_lookups_report_not_found(self, app_services: AppServices) -> None:
        for lookup in (app_services.accounts.get, app_services.transactions.get,
                       app_services.goals.get, app_services.ai.insight):
            with pytest.raises(NotFoundError):
                lookup(2**70)

    def test_search_offset_is_bounded(self, app_services: AppServices) -> None:
        with pytest.raises(ValidationError):
            app_services.transactions.search(TransactionQuery(offset=2**70))


class TestInputChecks:
    def test_statistics_needs_a_date_range(self, app_services: AppServices) -> None:
        with pytest.raises(ValidationError, match="date range"):
            app_services.statistics.report("last month")  # type: ignore[arg-type]

    def test_ai_mode_must_be_known(self, app_services: AppServices) -> None:
        with pytest.raises(ValidationError, match="automatic"):
            app_services.ai.set_mode("turbo")  # type: ignore[arg-type]

    def test_ai_question_must_be_text(self, app_services: AppServices) -> None:
        with pytest.raises(ValidationError):
            app_services.ai.prepare(42)  # type: ignore[arg-type]
        with pytest.raises(ValidationError, match="what the advisor"):
            app_services.ai.prepare(kind="poetry")  # type: ignore[arg-type]

    @pytest.mark.parametrize("path", [None, "", "   ", 3])
    def test_backup_paths_must_be_files(self, app_services: AppServices, path: object) -> None:
        with pytest.raises(ValidationError, match="Choose a file"):
            app_services.data.read_backup(path)  # type: ignore[arg-type]


def test_statistics_changes_are_unavailable_before_tracking(app_services: AppServices) -> None:
    s = app_services
    bank = s.accounts.create("Bank", opening_balance="100", opening_date=date(2026, 6, 1))
    food = s.categories.create("Food", CategoryKind.EXPENSE)
    s.transactions.create(TransactionDraft(bank.id, TransactionType.EXPENSE, "10", TODAY,
                                           food.id))
    report = s.statistics.report(DateRange(date(2026, 6, 1), TODAY))
    assert not report.comparison_complete
    assert (report.income_change, report.expenses_change, report.spending_change) == (
        None, None, None)
