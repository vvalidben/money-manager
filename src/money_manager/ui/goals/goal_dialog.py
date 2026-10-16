"""Create / edit goal dialog. Every rule is enforced by ``GoalService``."""

from datetime import date, timedelta

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from money_manager.core.errors import MoneyManagerError, ValidationError
from money_manager.domain.goals import GoalProgress
from money_manager.domain.money import parse_amount_text
from money_manager.domain.validation import MAX_GOAL_NAME_LENGTH
from money_manager.services import AppServices
from money_manager.ui.components import FormField
from money_manager.ui.formatting import format_money
from money_manager.ui.theme import Spacing
from money_manager.ui.transactions.filter_bar import to_qdate
from money_manager.ui.transactions.transaction_dialog import AMOUNT_INPUT_PATTERN

TRACK_NEW_ALLOCATION = "new_allocation"
TRACK_EXISTING_ALLOCATION = "existing_allocation"
TRACK_MANUAL = "manual"


def amount_edit(placeholder: str = "0.00") -> QLineEdit:
    edit = QLineEdit()
    edit.setPlaceholderText(placeholder)
    edit.setValidator(QRegularExpressionValidator(QRegularExpression(AMOUNT_INPUT_PATTERN), edit))
    return edit


class GoalDialog(QDialog):
    def __init__(
        self,
        services: AppServices,
        *,
        goal: GoalProgress | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._services = services
        self._original = goal
        self.saved: GoalProgress | None = None
        today = services.today()

        self.setWindowTitle("Edit goal" if goal else "New goal")
        self.setModal(True)
        self.setMinimumWidth(480)

        self.name_edit = QLineEdit()
        self.name_edit.setMaxLength(MAX_GOAL_NAME_LENGTH)
        self.name_edit.setPlaceholderText("e.g. Emergency Fund")
        self.target_edit = amount_edit()
        self.deadline_check = QCheckBox("Set a deadline")
        self.deadline_edit = QDateEdit(to_qdate(today + timedelta(days=365)))
        self.deadline_edit.setCalendarPopup(True)
        self.deadline_edit.setDisplayFormat("dd/MM/yyyy")
        self.deadline_edit.setMinimumDate(to_qdate(today))
        self.deadline_check.toggled.connect(self.deadline_edit.setEnabled)
        self.deadline_edit.setEnabled(False)
        deadline_box = QWidget()
        deadline_layout = QVBoxLayout(deadline_box)
        deadline_layout.setContentsMargins(0, 0, 0, 0)
        deadline_layout.addWidget(self.deadline_check)
        deadline_layout.addWidget(self.deadline_edit)
        self.description_edit = QPlainTextEdit()
        self.description_edit.setFixedHeight(60)
        self.description_edit.setPlaceholderText("Optional")

        # Keys match the ``field`` names of the service's ValidationError.
        self.fields: dict[str, FormField] = {
            "name": FormField("Name", self.name_edit),
            "target": FormField(f"Target ({services.base_currency})", self.target_edit),
            "deadline": FormField("Deadline", deadline_box, highlight=self.deadline_edit),
            "description": FormField("Description", self.description_edit),
        }

        self.form_error = QLabel()
        self.form_error.setObjectName("FormError")
        self.form_error.setWordWrap(True)
        self.form_error.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)
        layout.addWidget(self.form_error)
        for key in ("name", "target", "deadline", "description"):
            layout.addWidget(self.fields[key])

        if goal is None:
            self._build_tracking(layout)
        else:
            tracking = QLabel(
                "Tracked manually — not part of your balance."
                if goal.goal.is_manual
                else f"Money kept in the allocation “{goal.allocation_name}”."
            )
            tracking.setObjectName("MutedLabel")
            layout.addWidget(tracking)
            self._populate(goal)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        save = buttons.button(QDialogButtonBox.StandardButton.Save)
        save.setText("Save changes" if goal else "Create goal")
        save.setObjectName("PrimaryButton")
        buttons.accepted.connect(self.submit)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ----------------------------------------------------------- tracking

    def _build_tracking(self, layout: QVBoxLayout) -> None:
        heading = QLabel("Where is the money kept?")
        heading.setObjectName("FieldLabel")
        layout.addWidget(heading)

        self.tracking_group = QButtonGroup(self)
        self.new_radio = QRadioButton("In a new allocation for this goal (recommended)")
        self.existing_radio = QRadioButton("In an allocation I already have")
        self.manual_radio = QRadioButton("I'll track it manually (money outside the app)")
        for radio in (self.new_radio, self.existing_radio, self.manual_radio):
            self.tracking_group.addButton(radio)
        self.new_radio.setChecked(True)

        available = self._services.allocations.available()
        self.initial_edit = amount_edit("0.00 (optional)")
        self.fields["initial_amount"] = FormField(
            f"Move from Available now · {format_money(available)} available", self.initial_edit
        )

        self.allocation_combo = QComboBox()
        used = {g.goal.allocation_id for g in self._services.goals.list()}
        for allocation in self._services.allocations.list():
            if allocation.id not in used:
                self.allocation_combo.addItem(allocation.name, allocation.id)
        self.allocation_combo.setPlaceholderText("No free allocations")
        self.existing_radio.setEnabled(self.allocation_combo.count() > 0)
        self.fields["allocation_id"] = FormField("Allocation", self.allocation_combo)

        self.current_edit = amount_edit()
        self.fields["current"] = FormField("Saved so far", self.current_edit)

        for widget in (self.new_radio, self.fields["initial_amount"], self.existing_radio,
                       self.fields["allocation_id"], self.manual_radio, self.fields["current"]):
            layout.addWidget(widget)
        note = QLabel("Moving money into an allocation never changes your total balance.")
        note.setObjectName("MutedLabel")
        note.setWordWrap(True)
        layout.addWidget(note)
        self.tracking_group.buttonToggled.connect(lambda *_: self._update_tracking())
        self._update_tracking()

    @property
    def tracking(self) -> str:
        if self._original is not None:
            return TRACK_MANUAL if self._original.goal.is_manual else TRACK_NEW_ALLOCATION
        if self.existing_radio.isChecked():
            return TRACK_EXISTING_ALLOCATION
        return TRACK_MANUAL if self.manual_radio.isChecked() else TRACK_NEW_ALLOCATION

    def set_tracking(self, mode: str) -> None:
        {TRACK_NEW_ALLOCATION: self.new_radio, TRACK_EXISTING_ALLOCATION: self.existing_radio,
         TRACK_MANUAL: self.manual_radio}[mode].setChecked(True)

    def _update_tracking(self) -> None:
        mode = self.tracking
        self.fields["initial_amount"].setVisible(mode == TRACK_NEW_ALLOCATION)
        self.fields["allocation_id"].setVisible(mode == TRACK_EXISTING_ALLOCATION)
        self.fields["current"].setVisible(mode == TRACK_MANUAL)

    # --------------------------------------------------------------- submit

    def _populate(self, goal: GoalProgress) -> None:
        self.name_edit.setText(goal.goal.name)
        self.target_edit.setText(f"{goal.goal.target.amount}")
        if goal.goal.deadline is not None:
            self.deadline_check.setChecked(True)
            # An existing (possibly passed) deadline may be kept.
            self.deadline_edit.setMinimumDate(
                to_qdate(min(goal.goal.deadline, self._services.today())))
            self.deadline_edit.setDate(to_qdate(goal.goal.deadline))
        self.description_edit.setPlainText(goal.goal.description)

    @property
    def deadline(self) -> date | None:
        return self.deadline_edit.date().toPython() if self.deadline_check.isChecked() else None

    def submit(self) -> bool:
        for field in self.fields.values():
            field.set_error(None)
        self.form_error.hide()
        goals = self._services.goals
        try:
            target = parse_amount_text(self.target_edit.text(), "target")
            common = {
                "target": target,
                "deadline": self.deadline,
                "description": self.description_edit.toPlainText(),
            }
            name = self.name_edit.text()
            if self._original is not None:
                self.saved = goals.update(self._original.goal.id, name=name, **common)
            elif self.tracking == TRACK_EXISTING_ALLOCATION:
                allocation_id = self.allocation_combo.currentData()
                if allocation_id is None:
                    raise ValidationError("Choose an allocation.", "allocation_id")
                self.saved = goals.create_with_allocation(name, allocation_id=allocation_id,
                                                          **common)
            elif self.tracking == TRACK_MANUAL:
                current = _optional_amount(self.current_edit.text(), "current")
                self.saved = goals.create_manual(name, current=current, **common)
            else:
                initial = _optional_amount(self.initial_edit.text(), "initial_amount")
                self.saved = goals.create_with_new_allocation(name, initial_amount=initial,
                                                              **common)
        except ValidationError as exc:
            field = self.fields.get(exc.field or "")
            if field is not None and not field.isHidden():
                field.set_error(str(exc))
            else:
                self._show_form_error(str(exc))
            return False
        except MoneyManagerError as exc:
            self._show_form_error(str(exc))
            return False
        self.accept()
        return True

    def _show_form_error(self, message: str) -> None:
        self.form_error.setText(message)
        self.form_error.show()


def _optional_amount(text: str, field: str) -> object:
    """Blank means zero for optional amounts."""
    return parse_amount_text(text, field) if text.strip() else 0
