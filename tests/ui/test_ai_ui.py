"""AI settings card and the privacy consent dialog."""

from collections.abc import Iterator

import pytest
from PySide6.QtWidgets import QApplication, QDialog, QLabel

from money_manager.ai.privacy import DataDisclosure
from money_manager.ai.prompts import AIRequest
from money_manager.ai.providers import ProviderStatus
from money_manager.ai.settings import AIMode, AISettings
from money_manager.services import AppServices
from money_manager.ui.ai import consent_dialog
from money_manager.ui.ai.consent_dialog import DataConsentDialog, ask_consent
from money_manager.ui.ai.settings_card import AISettingsCard

KEY = "sk-ant-api03-uiTESTkey000000009876"
REQUEST = AIRequest("Be factual.", "<financial_analysis>Income: 12,000.00 MAD"
                                   "</financial_analysis>\n\nQuestion: Summarise.")


@pytest.fixture
def card(qapp: QApplication, app_services: AppServices) -> Iterator[AISettingsCard]:
    widget = AISettingsCard(app_services)
    widget.resize(700, 900)
    widget.show()
    yield widget
    widget.close()
    widget.deleteLater()


def choose(card: AISettingsCard, mode: AIMode) -> None:
    card.mode_combo.setCurrentIndex(card.mode_combo.findData(mode.value))


def label_texts(card: AISettingsCard) -> str:
    return "\n".join(label.text() for label in card.findChildren(QLabel))


class TestSettingsCard:
    def test_off_by_default(self, card: AISettingsCard) -> None:
        assert card.mode is AIMode.OFF
        assert not card.local_section.isVisible() and not card.online_section.isVisible()
        assert not card.test_button.isEnabled()
        assert "never your database" in label_texts(card)

    def test_sections_follow_the_mode(self, card: AISettingsCard) -> None:
        choose(card, AIMode.LOCAL)
        assert card.local_section.isVisible() and not card.online_section.isVisible()
        choose(card, AIMode.ONLINE)
        assert card.online_section.isVisible() and not card.local_section.isVisible()
        assert "api.anthropic.com" in card.online_notice.text()
        assert card.online_notice.objectName() == "PrivacyNotice"

    def test_save_local_settings(self, card: AISettingsCard, app_services: AppServices) -> None:
        choose(card, AIMode.LOCAL)
        card.local_model_combo.setEditText("")
        assert not card.save()
        assert card.fields["local_model"].error

        card.local_url_edit.setText("http://192.168.0.7:11434")
        card.local_model_combo.setEditText("llama3.2")
        assert not card.save()
        assert "this computer" in card.fields["local_url"].error

        card.local_url_edit.setText("http://127.0.0.1:11434/")
        assert card.save()
        assert app_services.ai.settings() == AISettings(AIMode.LOCAL, "http://127.0.0.1:11434",
                                                        "llama3.2")
        assert card.local_url_edit.text() == "http://127.0.0.1:11434"

    def test_saved_settings_are_shown_again(self, qapp: QApplication,
                                            app_services: AppServices) -> None:
        app_services.ai.save_settings(AISettings(AIMode.ONLINE, online_model="claude-sonnet-5",
                                                 timeout_seconds=90))
        card = AISettingsCard(app_services)
        assert (card.mode, card.online_model_edit.text(), card.timeout_spin.value()) == (
            AIMode.ONLINE, "claude-sonnet-5", 90)

    def test_api_key_is_saved_and_never_shown(self, card: AISettingsCard,
                                              app_services: AppServices) -> None:
        choose(card, AIMode.ONLINE)
        assert "No API key yet" in card.key_status_label.text()
        assert card.key_edit.echoMode() == card.key_edit.EchoMode.Password
        assert not card.remove_key_button.isEnabled()

        card.key_edit.setText(KEY)
        card.save_key()

        assert card.key_edit.text() == ""
        assert "…9876" in card.key_status_label.text()
        assert KEY not in label_texts(card)
        assert app_services.ai.key_status().hint == "…9876"

        card.remove_key()
        assert "No API key yet" in card.key_status_label.text()

    def test_invalid_key(self, card: AISettingsCard) -> None:
        choose(card, AIMode.ONLINE)
        card.key_edit.setText("not a key")
        card.save_key()
        assert card.fields["api_key"].error and card.key_edit.text() == ""

    def test_connection_check_uses_the_form_values(
        self, card: AISettingsCard, app_services: AppServices, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        seen: list[tuple[AISettings, bool]] = []

        def check(settings: AISettings, *, probe: bool = False) -> ProviderStatus:
            seen.append((settings, probe))
            return ProviderStatus(True, "Ready: llama3.2 on this computer.",
                                  ("llama3.2:latest", "qwen3:8b"))

        monkeypatch.setattr(app_services.ai, "check_availability", check)
        choose(card, AIMode.LOCAL)
        card.local_model_combo.setEditText("")
        shown = card.current_settings()
        card.find_models()

        assert seen == [(shown, True)]
        items = [card.local_model_combo.itemText(i) for i in range(card.local_model_combo.count())]
        assert items == ["llama3.2:latest", "qwen3:8b"]
        assert card.local_model_combo.currentText() == "llama3.2:latest"
        assert card.status_label.text().startswith("Ready")
        assert app_services.ai.settings() == AISettings()  # testing does not save

    def test_unavailable_provider_is_reported(self, card: AISettingsCard) -> None:
        choose(card, AIMode.ONLINE)
        card.test_connection()  # no key: nothing is contacted
        assert "API key" in card.status_label.text()
        assert card.status_label.objectName() == "FieldError"


def disclosure(online: bool) -> DataDisclosure:
    return DataDisclosure("Anthropic" if online else "Ollama",
                          "api.anthropic.com" if online else "this computer",
                          "claude-opus-5" if online else "llama3.2", online, REQUEST,
                          ("income, expenses, savings and investment totals and rates",))


class TestConsentDialog:
    def test_online_needs_an_explicit_acknowledgement(self, qapp: QApplication) -> None:
        item = disclosure(online=True)
        dialog = DataConsentDialog(item)

        assert dialog.preview.toPlainText() == REQUEST.payload_text
        assert dialog.preview.isReadOnly()
        assert "leaves this computer" in dialog.warning_label.text()
        assert dialog.send_button.text() == "Send to Anthropic"
        assert not dialog.send_button.isEnabled() and dialog.cancel_button.isDefault()

        dialog.accept()  # e.g. Enter pressed without ticking the box
        assert dialog.consent is None and dialog.result() != QDialog.DialogCode.Accepted

        dialog.acknowledge.setChecked(True)
        assert dialog.send_button.isEnabled()
        dialog.send_button.click()
        assert dialog.result() == QDialog.DialogCode.Accepted
        assert dialog.consent is not None and dialog.consent.covers(REQUEST, "api.anthropic.com")
        dialog.deleteLater()

    def test_local_needs_no_consent(self, qapp: QApplication) -> None:
        dialog = DataConsentDialog(disclosure(online=False))
        assert dialog.acknowledge.isHidden() and dialog.send_button.isEnabled()
        assert "Nothing is sent over the internet" in dialog.warning_label.text()
        dialog.send_button.click()
        assert dialog.consent is None
        dialog.deleteLater()

    def test_cancel_gives_no_consent(self, qapp: QApplication,
                                     monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(consent_dialog.DataConsentDialog, "exec",
                            lambda self: QDialog.DialogCode.Rejected)
        assert ask_consent(None, disclosure(online=True)) is None
