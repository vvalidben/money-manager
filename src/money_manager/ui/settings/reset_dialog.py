"""Reset confirmation: the user must type RESET; Cancel is the default."""

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from money_manager.core.errors import MoneyManagerError
from money_manager.services import AppServices
from money_manager.services.data_service import RESET_CONFIRMATION, ResetResult
from money_manager.ui.components import FormField
from money_manager.ui.theme import Spacing
from money_manager.core.i18n import tr


class ResetDialog(QDialog):
    def __init__(self, services: AppServices, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._services = services
        self.result_info: ResetResult | None = None
        self.setWindowTitle(tr("Reset all data"))
        self.setModal(True)
        self.setMinimumWidth(520)

        heading = QLabel(tr("Delete all of your data?"))
        heading.setObjectName("CardHeading")
        warning = QLabel(
            tr("This deletes every account, transaction, allocation, goal, subscription, "
            "investment, setting and AI insight. A safety backup of the database is written "
            "next to it first. Export a backup yourself if you want to keep a copy elsewhere."))
        warning.setObjectName("FormError")
        warning.setWordWrap(True)

        self.confirm_edit = QLineEdit()
        self.confirm_edit.setPlaceholderText(RESET_CONFIRMATION)
        self.confirm_field = FormField(tr("Type {0} to confirm", RESET_CONFIRMATION),
                                       self.confirm_edit)
        self.remove_key = QCheckBox(tr("Also remove the saved Anthropic API key"))

        buttons = QDialogButtonBox()
        self.reset_button = buttons.addButton(tr("Delete all data"),
                                              QDialogButtonBox.ButtonRole.DestructiveRole)
        self.reset_button.setObjectName("DangerButton")
        self.reset_button.setEnabled(False)
        self.reset_button.setAutoDefault(False)
        self.cancel_button = buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        self.cancel_button.setDefault(True)
        self.confirm_edit.textChanged.connect(
            lambda text: self.reset_button.setEnabled(text == RESET_CONFIRMATION))
        self.reset_button.clicked.connect(self.confirm)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)
        for widget in (heading, warning, self.confirm_field, self.remove_key, buttons):
            layout.addWidget(widget)

    def confirm(self) -> None:
        try:
            self.result_info = self._services.data.reset(
                self.confirm_edit.text(), remove_api_key=self.remove_key.isChecked())
        except MoneyManagerError as exc:
            self.confirm_field.set_error(str(exc))
            return
        self.accept()
