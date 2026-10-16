from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from money_manager.core.errors import ValidationError
from money_manager.domain.goals import (
    Goal,
    GoalProgress,
    GoalsSummary,
    GoalStatus,
    order_goals,
)
from money_manager.domain.money import Money
from money_manager.domain.validation import validate_goal

TODAY = date(2026, 6, 15)
START = date(2026, 1, 1)
EMERGENCY = Goal(1, "Emergency Fund", "", Money.of("20000"), START, None, 7, None)


def progress(current: str, goal: Goal = EMERGENCY, today: date = TODAY) -> GoalProgress:
    return GoalProgress(goal, Money.of(current), today)


class TestProgress:
    def test_requirements_example(self) -> None:
        item = progress("12500")

        assert item.progress == Decimal("0.6250")  # 62.5 %
        assert item.remaining == Money.of("7500")
        assert not item.is_complete

    @pytest.mark.parametrize(
        ("current", "expected"),
        [("0", "0.0000"), ("0.01", "0.0000"), ("1", "0.0001"), ("6666.67", "0.3333"),
         ("13333.33", "0.6667"), ("20000", "1.0000"), ("25000", "1.2500")],
    )
    def test_exact_and_rounded_half_up(self, current: str, expected: str) -> None:
        assert progress(current).progress == Decimal(expected)

    def test_over_funded(self) -> None:
        item = progress("25000")

        assert item.is_complete and item.status is GoalStatus.COMPLETED
        assert item.progress == Decimal("1.2500")
        assert item.bar_fraction == Decimal(1)  # only the bar is capped
        assert item.remaining == Money.zero()

    def test_negative_current_counts_as_nothing(self) -> None:
        # A backing allocation can never be negative, but the maths must not break.
        item = progress("-5")
        assert item.progress == Decimal("0.0000") and item.remaining == Money.of("20000")


class TestDeadlines:
    DATED = replace(EMERGENCY, deadline=date(2026, 12, 31))

    def test_no_deadline(self) -> None:
        item = progress("100")
        assert item.status is GoalStatus.IN_PROGRESS
        assert item.days_left is None and item.required_per_month is None

    def test_on_track_and_behind(self) -> None:
        # Start 1 Jan, deadline 31 Dec (364 days); by 15 Jun (165 days) a steady
        # saver has 20,000 × 165 / 364 = 9,065.93.
        expected = progress("0", self.DATED).expected_now

        assert expected == Money.of("9065.93")
        assert progress("9065.93", self.DATED).status is GoalStatus.ON_TRACK
        assert progress("9065.92", self.DATED).status is GoalStatus.BEHIND

    def test_days_left_and_required_per_month(self) -> None:
        item = progress("12500", self.DATED)

        assert item.days_left == 199
        # 7,500 ÷ (199 ÷ 30.436875) months = 1,147.118… → 1,147.12 per month
        assert item.required_per_month == Money.of("1147.12")

    def test_deadline_today(self) -> None:
        item = progress("12500", replace(EMERGENCY, deadline=TODAY))

        assert item.days_left == 0
        assert item.status is GoalStatus.BEHIND  # expected is the full target today
        assert item.required_per_month == Money.of("7500")

    def test_less_than_a_month_left_needs_everything_now(self) -> None:
        item = progress("12500", replace(EMERGENCY, deadline=date(2026, 6, 25)))
        assert item.required_per_month == Money.of("7500")

    def test_overdue(self) -> None:
        item = progress("100", self.DATED, today=date(2027, 1, 1))

        assert item.status is GoalStatus.OVERDUE
        assert item.days_left == -1
        assert item.required_per_month is None

    def test_completed_beats_overdue(self) -> None:
        item = progress("20000", self.DATED, today=date(2027, 1, 1))
        assert item.status is GoalStatus.COMPLETED

    def test_deadline_on_start_day(self) -> None:
        item = progress("0", replace(EMERGENCY, start_date=TODAY, deadline=TODAY))
        assert item.expected_now == Money.of("20000")


class TestSummary:
    def test_totals(self) -> None:
        goals = (
            progress("12500"),
            GoalProgress(replace(EMERGENCY, id=2, name="Car", target=Money.of("10000")),
                         Money.of("12000"), TODAY),
            GoalProgress(replace(EMERGENCY, id=3, name="Trip", target=Money.of("5000")),
                         Money.of("0"), TODAY),
        )

        summary = GoalsSummary(goals, "MAD")

        assert summary.total_target == Money.of("35000")
        assert summary.total_saved == Money.of("22500")  # the car counts only up to its target
        assert summary.overall_progress == Decimal("0.6429")
        assert summary.completed_count == 1
        assert len(summary.active) == 2
        assert summary.count(GoalStatus.IN_PROGRESS) == 2

    def test_empty(self) -> None:
        summary = GoalsSummary((), "MAD")
        assert summary.total_target == Money.zero() and summary.overall_progress is None
        assert summary.required_per_month == Money.zero()

    def test_order(self) -> None:
        later = replace(EMERGENCY, id=2, name="B", deadline=date(2027, 1, 1))
        sooner = replace(EMERGENCY, id=3, name="C", deadline=date(2026, 7, 1))
        undated = replace(EMERGENCY, id=4, name="A")
        done = replace(EMERGENCY, id=5, name="Done", target=Money.of("1"))

        items = [
            GoalProgress(later, Money.zero(), TODAY),
            GoalProgress(done, Money.of("1"), TODAY),  # complete
            GoalProgress(undated, Money.zero(), TODAY),
            GoalProgress(sooner, Money.zero(), TODAY),
        ]

        # Unfinished first by nearest deadline (undated last), completed at the end.
        assert [g.goal.name for g in order_goals(items)] == ["C", "B", "A", "Done"]


class TestValidation:
    def _validate(self, **overrides: object):
        fields: dict[str, object] = {
            "name": "Emergency Fund", "target": "20000", "deadline": None, "description": "",
        }
        fields.update(overrides)
        return validate_goal(currency="MAD", today=TODAY, **fields)  # type: ignore[arg-type]

    def test_valid(self) -> None:
        valid = self._validate(deadline=TODAY, description="  six months of rent ")
        assert valid.target == Money.of("20000") and valid.deadline == TODAY
        assert valid.description == "six months of rent"

    @pytest.mark.parametrize("target", ["0", "-100", 100.0, "1.234", "", "abc", None])
    def test_invalid_targets(self, target: object) -> None:
        with pytest.raises(ValidationError) as info:
            self._validate(target=target)
        assert info.value.field == "target"

    @pytest.mark.parametrize("deadline", [date(2026, 6, 14), "2027-01-01", date(2127, 1, 1)])
    def test_invalid_deadlines(self, deadline: object) -> None:
        with pytest.raises(ValidationError) as info:
            self._validate(deadline=deadline)
        assert info.value.field == "deadline"

    def test_an_edit_may_keep_a_passed_deadline(self) -> None:
        passed = date(2026, 5, 1)
        assert self._validate(deadline=passed, current_deadline=passed).deadline == passed

    def test_name_and_description_limits(self) -> None:
        with pytest.raises(ValidationError):
            self._validate(name="  ")
        with pytest.raises(ValidationError):
            self._validate(description="x" * 501)
