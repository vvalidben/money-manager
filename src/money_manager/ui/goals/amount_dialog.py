"""Add money to, withdraw from, or set the recorded amount of a goal."""

from enum import StrEnum

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QWidget

from money_manager.core.errors import MoneyManagerError, ValidationError
from money_manager.domain.goals import GoalProgress
from money_manager.domain.money import parse_amount_text
from money_manager.services import AppServices
from money_manager.ui.components import FormField
from money_manager.ui.formatting import format_money
from money_manager.ui.goals.goal_dialog import amount_edit
from money_manager.ui.theme import Spacing
from money_manager.core.i18n import tr


class AmountAction(StrEnum):
    ADD = "add"
    WITHDRAW = "withdraw"
    SET = "set"


class GoalAmountDialog(QDialog):
    def __init__(
        self,
        services: AppServices,
        goal: GoalProgress,
        action: AmountAction,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._services = services
        self._goal = goal
        self.action = action
        self.saved: GoalProgress | None = None
        name = goal.goal.name

        titles = {AmountAction.ADD: tr("Add money to {0}", name),
                  AmountAction.WITHDRAW: tr("Withdraw from {0}", name),
                  AmountAction.SET: tr("Update {0}", name)}
        self.setWindowTitle(titles[action])
        self.setModal(True)
        self.setMinimumWidth(420)

        explanation = QLabel(self._explanation())
        explanation.setObjectName("CardBody")
        explanation.setWordWrap(True)
        self.amount_edit = amount_edit()
        if action is AmountAction.SET:
            self.amount_edit.setText(f"{goal.saved.amount}")
        label = tr("Amount saved so far") if action is AmountAction.SET else tr("Amount")
        self.field = FormField(f"{label} ({services.base_currency})", self.amount_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok = buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok.setText({AmountAction.ADD: tr("Add money"), AmountAction.WITHDRAW: tr("Withdraw"),
                    AmountAction.SET: tr("Save")}[action])
        ok.setObjectName("PrimaryButton")
        buttons.accepted.connect(self.submit)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)
        layout.addWidget(explanation)
        layout.addWidget(self.field)
        layout.addWidget(buttons)

    def _explanation(self) -> str:
        goal = self._goal
        allocation = goal.allocation_name or "?"
        if self.action is AmountAction.SET:
            return (tr("Record how much you have saved for this goal outside the app. "
                    "This amount is not part of your balance."))
        if goal.goal.is_manual:
            verb = tr("Increase") if self.action is AmountAction.ADD else tr("Decrease")
            return tr("{0} the amount recorded for this goal. Your balance is not affected.", verb)
        if self.action is AmountAction.ADD:
            available = self._services.allocations.available()
            return (tr("Moves money from Available ({0}) into the allocation “{1}”. Your total "
                       "balance does not change.", format_money(available), allocation))
        return (tr("Moves money from the allocation “{0}” ({1}) back to Available. Your "
                   "total balance does not change.", allocation, format_money(goal.current)))

    def submit(self) -> bool:
        self.field.set_error(None)
        goals = self._services.goals
        goal_id = self._goal.goal.id
        try:
            amount = parse_amount_text(self.amount_edit.text())
            match self.action:
                case AmountAction.ADD:
                    self.saved = goals.contribute(goal_id, amount)
                case AmountAction.WITHDRAW:
                    self.saved = goals.withdraw(goal_id, amount)
                case AmountAction.SET:
                    self.saved = goals.set_manual_amount(goal_id, amount)
        except (ValidationError, MoneyManagerError) as exc:
            self.field.set_error(str(exc))
            return False
        self.accept()
        return True
