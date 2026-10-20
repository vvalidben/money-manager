"""AI provider settings on the Settings page. Every rule is enforced by ``AIService``."""

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from money_manager.ai.providers.anthropic_provider import API_HOST
from money_manager.ai.secrets import ANTHROPIC_KEY_ENV, KeySource, KeyStatus
from money_manager.ai.settings import (
    MAX_TIMEOUT_SECONDS,
    MIN_TIMEOUT_SECONDS,
    MODE_LABELS,
    AIMode,
    AISettings,
)
from money_manager.core.errors import MoneyManagerError, ValidationError
from money_manager.services import AppServices
from money_manager.ui.components import Card, FormField, compact_combo
from money_manager.ui.theme import Spacing, set_style_property
from money_manager.core.i18n import tr

logger = logging.getLogger(__name__)

FORM_MAX_WIDTH = 640

INTRO_TEXT = (
    tr("AI features are optional and off unless you choose a provider. They receive a summary "
    "calculated by Money Manager, never your database, transaction descriptions or account "
    "names.")
)
LOCAL_NOTE = tr("Runs on this computer with Ollama. Nothing is sent over the internet.")
ONLINE_NOTICE = (
    tr("Online AI sends a summary of your finances to Anthropic ({0}). Before "
       "every request you will see exactly what would be sent, and nothing is "
       "sent unless you confirm.", API_HOST)
)
AUTO_NOTE = (
    tr("Automatic uses the local model when Ollama is running with it, and otherwise the online "
    "provider. Online requests still show what would be sent and wait for your confirmation.")
)


class AISettingsCard(Card):
    def __init__(self, services: AppServices, parent: QWidget | None = None) -> None:
        super().__init__(tr("AI assistant"), parent)
        self._ai = services.ai

        intro = QLabel(INTRO_TEXT)
        intro.setObjectName("CardBody")
        intro.setWordWrap(True)

        self.mode_combo = QComboBox()
        self.mode_combo.setAccessibleName(tr("Provider"))
        for mode, label in MODE_LABELS.items():
            self.mode_combo.addItem(tr(label), mode.value)
        self.mode_combo.currentIndexChanged.connect(self._update_sections)
        compact_combo(self.mode_combo, 18)

        # Local model
        self.local_url_edit = QLineEdit()
        self.local_url_edit.setPlaceholderText("http://localhost:11434")
        self.local_model_combo = QComboBox()
        self.local_model_combo.setAccessibleName(tr("Local model"))
        self.local_model_combo.setEditable(True)
        self.local_model_combo.setPlaceholderText(tr("e.g. llama3.2"))
        compact_combo(self.local_model_combo, 14)
        self.find_models_button = QPushButton(tr("Find installed models"))
        self.find_models_button.clicked.connect(self.find_models)
        model_row = QWidget()
        model_layout = QHBoxLayout(model_row)
        model_layout.setContentsMargins(0, 0, 0, 0)
        model_layout.addWidget(self.local_model_combo, 1)
        model_layout.addWidget(self.find_models_button)
        local_note = QLabel(LOCAL_NOTE)
        local_note.setObjectName("MutedLabel")
        local_note.setWordWrap(True)

        # Online provider
        self.online_notice = QLabel(ONLINE_NOTICE)
        self.online_notice.setObjectName("PrivacyNotice")
        self.online_notice.setWordWrap(True)
        self.online_model_edit = QLineEdit()
        self.key_status_label = QLabel()
        self.key_status_label.setObjectName("MutedLabel")
        self.key_status_label.setWordWrap(True)
        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_edit.setPlaceholderText(tr("Paste an Anthropic API key"))
        self.save_key_button = QPushButton(tr("Save key"))
        self.save_key_button.clicked.connect(self.save_key)
        self.remove_key_button = QPushButton(tr("Remove key"))
        self.remove_key_button.clicked.connect(self.remove_key)
        key_row = QWidget()
        key_layout = QHBoxLayout(key_row)
        key_layout.setContentsMargins(0, 0, 0, 0)
        key_layout.addWidget(self.key_edit, 1)
        key_layout.addWidget(self.save_key_button)
        key_layout.addWidget(self.remove_key_button)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setAccessibleName(tr("Timeout"))
        self.timeout_spin.setRange(MIN_TIMEOUT_SECONDS, MAX_TIMEOUT_SECONDS)
        self.timeout_spin.setSuffix(" seconds")
        # Typed or changed with the arrow keys; the styled box has no room for arrows.
        self.timeout_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)

        # Keys match the ``field`` names of the service's ValidationError.
        self.fields: dict[str, FormField] = {
            "mode": FormField(tr("Provider"), self.mode_combo),
            "local_url": FormField(tr("Ollama address"), self.local_url_edit),
            "local_model": FormField(tr("Local model"), model_row, highlight=self.local_model_combo),
            "online_model": FormField(tr("Claude model"), self.online_model_edit),
            "api_key": FormField(tr("API key"), key_row, highlight=self.key_edit),
            "timeout_seconds": FormField(tr("Timeout"), self.timeout_spin),
        }

        for field in self.fields.values():
            field.setMaximumWidth(FORM_MAX_WIDTH)
        self.timeout_spin.setMaximumWidth(200)

        self.local_section = self._section(self.fields["local_url"], self.fields["local_model"],
                                           local_note)
        self.online_section = self._section(self.online_notice, self.fields["online_model"],
                                            self.fields["api_key"], self.key_status_label)

        self.save_button = QPushButton(tr("Save AI settings"))
        self.save_button.setObjectName("PrimaryButton")
        self.save_button.clicked.connect(self.save)
        self.test_button = QPushButton(tr("Test connection"))
        self.test_button.setToolTip(tr("Checks the provider without sending any financial data."))
        self.test_button.clicked.connect(self.test_connection)
        buttons = QHBoxLayout()
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.test_button)
        buttons.addStretch(1)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.status_label.hide()

        self.auto_note = QLabel(AUTO_NOTE)
        self.auto_note.setObjectName("MutedLabel")
        self.auto_note.setWordWrap(True)

        self.body.addWidget(intro)
        self.body.addWidget(self.fields["mode"])
        self.body.addWidget(self.auto_note)
        self.body.addWidget(self.local_section)
        self.body.addWidget(self.online_section)
        self.body.addWidget(self.fields["timeout_seconds"])
        self.body.addLayout(buttons)
        self.body.addWidget(self.status_label)
        self.load()

    @staticmethod
    def _section(*widgets: QWidget) -> QWidget:
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)
        for widget in widgets:
            layout.addWidget(widget)
        return section

    # --------------------------------------------------------------- state

    def load(self) -> None:
        try:
            settings = self._ai.settings()
        except MoneyManagerError as exc:
            self._show_status(str(exc), error=True)
            settings = AISettings()
        self.mode_combo.setCurrentIndex(self.mode_combo.findData(settings.mode.value))
        self.local_url_edit.setText(settings.local_url)
        self.local_model_combo.setEditText(settings.local_model)
        self.online_model_edit.setText(settings.online_model)
        self.timeout_spin.setValue(settings.timeout_seconds)
        self._show_key_status(self._ai.key_status())
        self._update_sections()

    @property
    def mode(self) -> AIMode:
        return AIMode(self.mode_combo.currentData())

    def current_settings(self) -> AISettings:
        """What the form shows; validated by the service."""
        return AISettings(mode=self.mode, local_url=self.local_url_edit.text(),
                          local_model=self.local_model_combo.currentText(),
                          online_model=self.online_model_edit.text(),
                          timeout_seconds=self.timeout_spin.value())

    def _update_sections(self) -> None:
        self.local_section.setVisible(self.mode in (AIMode.LOCAL, AIMode.AUTO))
        self.online_section.setVisible(self.mode in (AIMode.ONLINE, AIMode.AUTO))
        self.auto_note.setVisible(self.mode is AIMode.AUTO)
        self.test_button.setEnabled(self.mode is not AIMode.OFF)

    # ------------------------------------------------------------- actions

    def save(self) -> bool:
        self._clear_errors()
        try:
            saved = self._ai.save_settings(self.current_settings())
        except ValidationError as exc:
            self._show_error(exc)
            return False
        except MoneyManagerError as exc:
            self._show_status(str(exc), error=True)
            return False
        self.local_url_edit.setText(saved.local_url)
        self._show_status(tr("AI settings saved.") if saved.mode is not AIMode.OFF
                          else tr("AI features are off."))
        return True

    def test_connection(self) -> None:
        """Contacts the provider (no financial data) with the settings as shown."""
        self._clear_errors()
        self._show_status(tr("Checking…"))
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            status = self._ai.check_availability(self.current_settings(), probe=True)
        except ValidationError as exc:
            self._show_error(exc)
            return
        except MoneyManagerError as exc:
            self._show_status(str(exc), error=True)
            return
        finally:
            QApplication.restoreOverrideCursor()
        if status.models:
            self._offer_models(status.models)
        self._show_status(status.message, error=not status.available)

    def find_models(self) -> None:
        self.test_connection()

    def save_key(self) -> None:
        self._clear_errors()
        try:
            status = self._ai.save_api_key(self.key_edit.text())
        except ValidationError as exc:
            self._show_error(exc)
            return
        except MoneyManagerError as exc:
            self._show_status(str(exc), error=True)
            return
        finally:
            self.key_edit.clear()  # the key is never displayed again
        self._show_key_status(status)
        self._show_status(tr("API key saved in {0}.", self._ai.key_location))

    def remove_key(self) -> None:
        self._clear_errors()
        try:
            status = self._ai.remove_api_key()
        except MoneyManagerError as exc:
            self._show_status(str(exc), error=True)
            return
        self._show_key_status(status)
        self._show_status(tr("Stored API key removed."))

    # -------------------------------------------------------------- helpers

    def _offer_models(self, models: tuple[str, ...]) -> None:
        current = self.local_model_combo.currentText()
        self.local_model_combo.clear()
        self.local_model_combo.addItems(list(models))
        self.local_model_combo.setEditText(current or models[0])

    def _show_key_status(self, status: KeyStatus) -> None:
        match status.source:
            case KeySource.STORED:
                text = tr("A key ending in {0} is stored in {1}.", status.hint, self._ai.key_location)
            case KeySource.ENVIRONMENT:
                text = tr("Using the key ending in {0} from {1}.", status.hint, ANTHROPIC_KEY_ENV)
            case _:
                text = (tr("No API key yet. Keys are kept in {0}, never in the database.", self._ai.key_location))
        self.key_status_label.setText(text)
        self.remove_key_button.setEnabled(status.source is KeySource.STORED)

    def _clear_errors(self) -> None:
        for field in self.fields.values():
            field.set_error(None)

    def _show_error(self, exc: ValidationError) -> None:
        field = self.fields.get(exc.field or "")
        if field is not None and field.isVisibleTo(self):
            field.set_error(str(exc))
            self._show_status("", error=False)
        else:
            self._show_status(str(exc), error=True)

    def _show_status(self, message: str, *, error: bool = False) -> None:
        self.status_label.setText(message)
        self.status_label.setObjectName("FieldError" if error else "MutedLabel")
        set_style_property(self.status_label, "error", error)
        self.status_label.setVisible(bool(message))
