"""Privacy warning shown before financial information is sent to an AI provider.

The dialog shows where the data goes, what is and is never included, and the
exact text that would be sent. For an online provider the send button stays
disabled until the user ticks the acknowledgement; Cancel is the default.
Only an accepted dialog produces an ``OnlineConsent``.
"""

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from money_manager.ai.privacy import DataDisclosure, OnlineConsent
from money_manager.ui.theme import Spacing
from money_manager.core.i18n import tr


def _bullets(items: tuple[str, ...]) -> str:
    return "\n".join(f"•  {item}" for item in items)


class DataConsentDialog(QDialog):
    def __init__(self, disclosure: DataDisclosure, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._disclosure = disclosure
        self.consent: OnlineConsent | None = None

        self.setWindowTitle(disclosure.title)
        self.setModal(True)
        self.setMinimumWidth(640)

        heading = QLabel(disclosure.title)
        heading.setObjectName("CardHeading")
        self.warning_label = QLabel(disclosure.warning)
        self.warning_label.setObjectName("PrivacyNotice" if disclosure.is_online else "CardBody")
        self.warning_label.setWordWrap(True)

        destination = QLabel(tr("Destination: {0} ({1}) · model {2}", disclosure.provider, disclosure.destination, disclosure.model))
        destination.setObjectName("MutedLabel")
        included = QLabel(tr("Included:\n") + _bullets(disclosure.included))
        included.setObjectName("CardBody")
        included.setWordWrap(True)
        never = QLabel(tr("Never sent:\n") + _bullets(disclosure.never_sent))
        never.setObjectName("CardBody")
        never.setWordWrap(True)

        preview_label = QLabel(tr("Exactly what will be sent:"))
        preview_label.setObjectName("FieldLabel")
        self.preview = QPlainTextEdit(disclosure.request.payload_text)
        self.preview.setReadOnly(True)
        self.preview.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.preview.setMinimumHeight(240)

        self.acknowledge = QCheckBox(tr("I understand that this information will leave my computer."))
        self.acknowledge.setVisible(disclosure.is_online)

        buttons = QDialogButtonBox()
        self.send_button: QPushButton = buttons.addButton(
            tr("Send to {0}", disclosure.provider) if disclosure.is_online else tr("Analyse"),
            QDialogButtonBox.ButtonRole.AcceptRole)
        self.send_button.setObjectName("PrimaryButton")
        self.cancel_button = buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        self.cancel_button.setDefault(True)
        self.send_button.setAutoDefault(False)
        self.send_button.setEnabled(not disclosure.is_online)
        self.acknowledge.toggled.connect(self.send_button.setEnabled)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)
        for widget in (heading, self.warning_label, destination, included, never,
                       preview_label, self.preview, self.acknowledge, buttons):
            layout.addWidget(widget)

    def accept(self) -> None:
        if self._disclosure.is_online:
            if not self.acknowledge.isChecked():
                return
            self.consent = self._disclosure.accept()
        super().accept()


def ask_consent(parent: QWidget | None, disclosure: DataDisclosure) -> OnlineConsent | None:
    """Show the warning for an online request; the consent, or None if cancelled."""
    dialog = DataConsentDialog(disclosure, parent)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return dialog.consent
