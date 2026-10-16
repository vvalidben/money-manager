from collections.abc import Iterator
from datetime import date, timedelta
from decimal import Decimal

import pytest
from PySide6.QtWidgets import QApplication, QDialog

from money_manager.domain.entities import Account
from money_manager.domain.goals import Goal, GoalProgress, GoalStatus
from money_manager.domain.money import Money
from money_manager.services import AppServices
from money_manager.ui import dialogs
from money_manager.ui.goals.amount_dialog import AmountAction, GoalAmountDialog
from money_manager.ui.goals.goal_dialog import (
    TRACK_EXISTING_ALLOCATION,
    TRACK_MANUAL,
    GoalDialog,
)
from money_manager.ui.goals.goals_page import KEEP_MONEY, RELEASE_MONEY, GoalsPage
from money_manager.ui.goals.view_model import goal_card_view, summary_stats
from money_manager.ui.dashboard.dashboard_page import DashboardPage
from money_manager.ui.pages import DASHBOARD_PAGE_KEY, GOALS_PAGE_KEY, PAGES
from money_manager.ui.transactions.filter_bar import to_qdate
from tests.services.support import OPENING_DATE, TODAY

GOALS_SPEC = next(spec for spec in PAGES if spec.key == GOALS_PAGE_KEY)
DASHBOARD_SPEC = next(spec for spec in PAGES if spec.key == DASHBOARD_PAGE_KEY)


@pytest.fixture
def bank(app_services: AppServices) -> Account:
    return app_services.accounts.create("Bank", opening_balance="30000", opening_date=OPENING_DATE)


@pytest.fixture
def page(qapp: QApplication, app_services: AppServices) -> Iterator[GoalsPage]:
    widget = GoalsPage(GOALS_SPEC, app_services)
    widget.resize(1200, 900)
    widget.show()
    widget.on_shown()
    yield widget
    widget.close()
    widget.deleteLater()


def _goal(**overrides: object) -> Goal:
    fields: dict[str, object] = {
        "id": 1, "name": "Emergency Fund", "description": "", "target": Money.of("20000"),
        "start_date": date(2026, 1, 1), "deadline": None, "allocation_id": 3,
        "manual_amount": None,
    }
    fields.update(overrides)
    return Goal(**fields)  # type: ignore[arg-type]


class TestViewModel:
    def test_requirements_example(self) -> None:
        view = goal_card_view(GoalProgress(_goal(), Money.of("12500"), TODAY, "Emergency Fund"))

        assert view.amounts == "12,500.00 MAD of 20,000.00 MAD"
        assert view.percent == "62.5%"
        assert view.remaining == "7,500.00 MAD to go"
        assert view.status_text == "● In progress"
        assert view.tracking == "Money kept in the allocation “Emergency Fund”"
        assert view.pace == "Set a deadline to see how much to save each month."

    def test_deadline_texts(self) -> None:
        dated = _goal(deadline=TODAY + timedelta(days=1))
        assert goal_card_view(GoalProgress(dated, Money.zero(), TODAY)).deadline == (
            "Due 16 Jun 2026 · 1 day left"
        )
        overdue = GoalProgress(_goal(deadline=TODAY - timedelta(days=3)), Money.zero(), TODAY)
        view = goal_card_view(overdue)
        assert view.deadline.endswith("overdue by 3 days")
        assert view.status_text == "! Overdue" and view.status_level == "poor"
        today = goal_card_view(GoalProgress(_goal(deadline=TODAY), Money.zero(), TODAY))
        assert today.deadline.endswith("due today")

    def test_completed_and_manual(self) -> None:
        manual = _goal(allocation_id=None, manual_amount=Money.of("25000"))
        view = goal_card_view(GoalProgress(manual, Money.of("25000"), TODAY))

        assert view.percent == "125.0%" and view.bar_fraction == Decimal(1)
        assert view.remaining == "Target reached"
        assert view.status_text == "✓ Completed"
        assert view.is_manual and "not part of your balance" in view.tracking

    def test_summary_stats(self, app_services: AppServices, bank: Account) -> None:
        app_services.goals.create_with_new_allocation(
            "Laptop", target="12000", initial_amount="1500", deadline=TODAY + timedelta(days=40))
        stats = summary_stats(app_services.goals.summary())

        assert stats[0].value == "1,500.00 MAD"
        assert stats[0].caption == "of 12,000.00 MAD · 12.5%"
        assert stats[1].value == "1"
        assert stats[3].caption == "Everything is on schedule"


class TestGoalDialog:
    def test_create_with_new_allocation(
        self, qapp: QApplication, app_services: AppServices, bank: Account
    ) -> None:
        dialog = GoalDialog(app_services)
        dialog.name_edit.setText("Emergency Fund")
        dialog.target_edit.setText("20 000")
        dialog.initial_edit.setText("12 500")
        dialog.deadline_check.setChecked(True)
        dialog.deadline_edit.setDate(to_qdate(date(2026, 12, 31)))

        assert dialog.submit()

        saved = dialog.saved
        assert saved is not None and saved.progress == Decimal("0.6250")
        assert saved.goal.deadline == date(2026, 12, 31)
        assert app_services.allocations.available() == Money.of("17500")

    def test_create_with_existing_allocation(
        self, qapp: QApplication, app_services: AppServices, bank: Account
    ) -> None:
        savings = app_services.allocations.create("Savings", initial_amount="5000")
        dialog = GoalDialog(app_services)
        dialog.set_tracking(TRACK_EXISTING_ALLOCATION)
        dialog.name_edit.setText("House")
        dialog.target_edit.setText("100000")

        assert dialog.allocation_combo.currentData() == savings.id
        assert dialog.submit()
        assert dialog.saved is not None and dialog.saved.current == Money.of("5000")

    def test_allocations_already_backing_a_goal_are_not_offered(
        self, qapp: QApplication, app_services: AppServices, bank: Account
    ) -> None:
        app_services.goals.create_with_new_allocation("Car", target="100")

        dialog = GoalDialog(app_services)

        assert dialog.allocation_combo.count() == 0
        assert not dialog.existing_radio.isEnabled()

    def test_create_manual(self, qapp: QApplication, app_services: AppServices) -> None:
        dialog = GoalDialog(app_services)
        dialog.set_tracking(TRACK_MANUAL)
        dialog.name_edit.setText("Gift")
        dialog.target_edit.setText("300")
        dialog.current_edit.setText("120")

        assert not dialog.fields["current"].isHidden()
        assert dialog.fields["initial_amount"].isHidden()
        assert dialog.submit()
        assert dialog.saved is not None and dialog.saved.current == Money.of("120")

    @pytest.mark.parametrize(
        ("target", "initial", "field", "message"),
        [
            ("0", "", "target", "greater than zero"),
            ("", "", "target", "Enter an amount"),
            ("1,200", "", "target", "ambiguous"),
            ("100", "99999", "initial_amount", "Available holds"),
        ],
    )
    def test_errors_are_inline(
        self, qapp: QApplication, app_services: AppServices, bank: Account, target: str,
        initial: str, field: str, message: str,
    ) -> None:
        dialog = GoalDialog(app_services)
        dialog.name_edit.setText("Car")
        dialog.target_edit.setText(target)
        dialog.initial_edit.setText(initial)

        assert not dialog.submit()

        error = dialog.fields[field].error or dialog.form_error.text()
        assert message in error
        assert app_services.goals.list() == []

    def test_target_error_does_not_mention_transactions(
        self, qapp: QApplication, app_services: AppServices
    ) -> None:
        dialog = GoalDialog(app_services)
        dialog.name_edit.setText("Car")
        dialog.target_edit.setText("0")
        dialog.submit()
        assert dialog.fields["target"].error == "Amount must be greater than zero."

    def test_edit(self, qapp: QApplication, app_services: AppServices) -> None:
        goal = app_services.goals.create_manual("Trip", target="100", deadline=TODAY)
        dialog = GoalDialog(app_services, goal=goal)

        assert dialog.name_edit.text() == "Trip" and dialog.target_edit.text() == "100.00"
        assert dialog.deadline_check.isChecked()
        dialog.target_edit.setText("250")
        dialog.deadline_check.setChecked(False)
        assert dialog.submit()

        updated = app_services.goals.get(goal.goal.id)
        assert updated.goal.target == Money.of("250") and updated.goal.deadline is None


class TestAmountDialog:
    def test_add_and_withdraw(self, qapp: QApplication, app_services: AppServices,
                              bank: Account) -> None:
        goal = app_services.goals.create_with_new_allocation("Car", target="10000")

        add = GoalAmountDialog(app_services, goal, AmountAction.ADD)
        add.amount_edit.setText("2 500")
        assert add.submit() and add.saved is not None
        assert add.saved.current == Money.of("2500")

        withdraw = GoalAmountDialog(app_services, add.saved, AmountAction.WITHDRAW)
        withdraw.amount_edit.setText("3000")
        assert not withdraw.submit()
        assert "holds 2,500.00 MAD" in withdraw.field.error

    def test_set_manual_amount(self, qapp: QApplication, app_services: AppServices) -> None:
        goal = app_services.goals.create_manual("Gift", target="300", current="20")
        dialog = GoalAmountDialog(app_services, goal, AmountAction.SET)

        assert dialog.amount_edit.text() == "20.00"
        dialog.amount_edit.setText("150")
        assert dialog.submit()
        assert app_services.goals.get(goal.goal.id).current == Money.of("150")


class TestGoalsPage:
    def test_empty_state(self, page: GoalsPage) -> None:
        assert not page.empty_state.isHidden()
        assert page.cards == []

    def test_cards_and_summary(self, page: GoalsPage, app_services: AppServices,
                               bank: Account) -> None:
        app_services.goals.create_with_new_allocation("Emergency Fund", target="20000",
                                                      initial_amount="12500")
        app_services.goals.create_manual("Gift", target="100")

        page.refresh()

        assert [card.view.name for card in page.cards] == ["Emergency Fund", "Gift"]
        assert page.card_for(page.cards[0].view.goal_id).view.percent == "62.5%"
        assert page.stat_cards[0].value == "12,500.00 MAD"
        assert page.empty_state.isHidden()

    def test_add_money_from_card(self, page: GoalsPage, app_services: AppServices,
                                 bank: Account, monkeypatch: pytest.MonkeyPatch) -> None:
        goal = app_services.goals.create_with_new_allocation("Car", target="1000")
        page.refresh()

        def submit(dialog: GoalAmountDialog) -> int:
            dialog.amount_edit.setText("250")
            return QDialog.DialogCode.Accepted if dialog.submit() else QDialog.DialogCode.Rejected

        monkeypatch.setattr(GoalAmountDialog, "exec", submit)
        page.card_for(goal.goal.id).primary_button.click()

        assert page.card_for(goal.goal.id).view.percent == "25.0%"

    @pytest.mark.parametrize(("choice", "archived"), [(KEEP_MONEY, False), (RELEASE_MONEY, True)])
    def test_delete_backed_goal_asks_what_to_do_with_the_money(
        self, page: GoalsPage, app_services: AppServices, bank: Account,
        monkeypatch: pytest.MonkeyPatch, choice: str, archived: bool,
    ) -> None:
        goal = app_services.goals.create_with_new_allocation("Car", target="1000",
                                                             initial_amount="400")
        page.refresh()
        monkeypatch.setattr(dialogs, "choose", lambda *_args: choice)

        page.card_for(goal.goal.id).delete_button.click()

        assert page.cards == []
        allocation = app_services.allocations.get(goal.goal.allocation_id)
        assert allocation.is_archived is archived
        expected_available = "30000" if archived else "29600"
        assert app_services.allocations.available() == Money.of(expected_available)

    def test_cancel_delete(self, page: GoalsPage, app_services: AppServices, bank: Account,
                           monkeypatch: pytest.MonkeyPatch) -> None:
        goal = app_services.goals.create_with_new_allocation("Car", target="1000")
        page.refresh()
        monkeypatch.setattr(dialogs, "choose", lambda *_args: None)

        page.card_for(goal.goal.id).delete_button.click()

        assert len(page.cards) == 1

    def test_delete_manual_goal_confirms(self, page: GoalsPage, app_services: AppServices,
                                         monkeypatch: pytest.MonkeyPatch) -> None:
        goal = app_services.goals.create_manual("Gift", target="100")
        page.refresh()
        asked: list[str] = []
        monkeypatch.setattr(dialogs, "confirm_destructive",
                            lambda _p, _t, message, *_a: asked.append(message) or True)

        page.card_for(goal.goal.id).delete_button.click()

        assert "Gift" in asked[0] and page.cards == []


def test_dashboard_shows_goals(qapp: QApplication, app_services: AppServices,
                               bank: Account) -> None:
    app_services.goals.create_with_new_allocation("Laptop", target="12000", initial_amount="1500",
                                                  deadline=TODAY + timedelta(days=40))
    app_services.goals.create_manual("Gift", target="100", current="100")
    dashboard = DashboardPage(DASHBOARD_SPEC, app_services)
    requested: list[str] = []
    dashboard.navigate_requested.connect(requested.append)
    dashboard.show()
    try:
        dashboard.on_shown()

        views = dashboard.goals_card.views
        assert [v.name for v in views] == ["Laptop", "Gift"]  # unfinished first
        # Started today, so a steady saver needs nothing yet: on track.
        assert views[0].status_text == "✓ On track"
        assert dashboard.goals_card.empty_label.isHidden()
        dashboard.goals_card.view_all_button.click()
        assert requested == [GOALS_PAGE_KEY]
    finally:
        dashboard.close()
        dashboard.deleteLater()


def test_status_enum_is_covered() -> None:
    from money_manager.ui.goals.view_model import STATUS_LEVEL, STATUS_TEXT

    assert set(STATUS_TEXT) == set(GoalStatus) == set(STATUS_LEVEL)
