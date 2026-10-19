"""Settings page: currency, export/import, reset safeguards, privacy and rebuild."""

from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QDialog, QLabel

from money_manager.ai.settings import AIMode
from money_manager.core.config import AppConfig
from money_manager.domain.entities import TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.money import Money
from money_manager.persistence.database import Database
from money_manager.services import AppServices
from money_manager.ui import dialogs
from money_manager.ui.pages import PAGES, SETTINGS_PAGE_KEY, SettingsPage
from money_manager.ui.settings import cards
from money_manager.ui.settings.reset_dialog import ResetDialog
from tests.services.support import fixed_today

SPEC = next(spec for spec in PAGES if spec.key == SETTINGS_PAGE_KEY)


@pytest.fixture
def page(qapp: QApplication, app_config: AppConfig,
         app_services: AppServices) -> Iterator[SettingsPage]:
    widget = SettingsPage(SPEC, app_config, app_services)
    widget.resize(1100, 900)
    widget.show()
    reloads: list[str] = []
    widget.reload_requested.connect(reloads.append)
    widget.reloads = reloads  # type: ignore[attr-defined]
    yield widget
    widget.close()
    widget.deleteLater()


@pytest.fixture
def data(app_services: AppServices) -> AppServices:
    bank = app_services.accounts.create("Bank", opening_balance="100", opening_date=date(2026, 1, 1))
    salary = app_services.categories.create("Salary", CategoryKind.INCOME)
    app_services.transactions.create(TransactionDraft(bank.id, TransactionType.INCOME, "900",
                                                      fixed_today(), salary.id))
    return app_services


def texts(widget: object) -> str:
    return "\n".join(label.text() for label in widget.findChildren(QLabel))  # type: ignore[attr-defined]


def test_every_section_is_present(page: SettingsPage, app_config: AppConfig) -> None:
    shown = texts(page)
    for heading in ("Local data storage", "Currency", "AI assistant", "Export and import",
                    "Privacy", "Reset application data", "About Money Manager"):
        assert heading in shown
    assert str(app_config.database_path) in shown and "MONEY_MANAGER_DATA_DIR" in shown
    assert "MoneyManager.ini" in shown


def test_storage_card_shows_the_configuration_file(qapp: QApplication, tmp_path: Path) -> None:
    ini = tmp_path / "MoneyManager.ini"
    without = cards.StorageCard(AppConfig(data_dir=tmp_path))
    with_file = cards.StorageCard(AppConfig(data_dir=tmp_path, config_file=ini))
    try:
        assert "Configuration file\nNone" in texts(without)
        assert str(ini) in texts(with_file)
    finally:
        without.deleteLater()
        with_file.deleteLater()


def test_privacy_information(page: SettingsPage) -> None:
    privacy = " ".join(page.privacy_card.points)
    assert "stored only on this computer" in privacy
    assert "Online AI (Anthropic) sends selected financial information" in privacy
    assert "Local AI (Ollama) processes the financial summary on this computer" in privacy
    assert "API keys are sensitive" in privacy


def test_open_data_folder(page: SettingsPage, app_config: AppConfig,
                          monkeypatch: pytest.MonkeyPatch) -> None:
    opened: list[Path] = []
    monkeypatch.setattr(cards, "open_folder", opened.append)
    page.storage_card.open_button.click()
    assert opened == [app_config.data_dir]


def test_about(page: SettingsPage) -> None:
    rows = dict(page.about_card.rows)
    assert rows["Version"].startswith("Money Manager ") and rows["Currency"] == "MAD"
    assert rows["Data schema"].isdigit()


class TestCurrency:
    def test_change_before_any_account(self, page: SettingsPage,
                                       app_services: AppServices) -> None:
        card = page.currency_card
        assert card.combo.isEnabled() and card.combo.currentData() == "MAD"
        card.combo.setCurrentIndex(card.combo.findData("EUR"))
        card.save_button.click()
        assert app_services.settings.currency() == "EUR"
        assert page.reloads == [SETTINGS_PAGE_KEY]  # type: ignore[attr-defined]

    def test_locked_once_accounts_exist(self, page: SettingsPage, data: AppServices) -> None:
        page.on_shown()
        card = page.currency_card
        assert not card.combo.isEnabled() and not card.save_button.isEnabled()
        assert "cannot be changed once accounts exist" in card.note.text()


def test_ai_card_offers_automatic(page: SettingsPage) -> None:
    card = page.ai_card
    card.mode_combo.setCurrentIndex(card.mode_combo.findData(AIMode.AUTO.value))
    assert card.local_section.isVisible() and card.online_section.isVisible()
    assert card.auto_note.isVisible() and "confirmation" in card.auto_note.text()


class TestExportImport:
    def test_export_backup_and_csv(self, page: SettingsPage, data: AppServices,
                                   tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        targets = iter([tmp_path / "backup.json", tmp_path / "transactions.csv"])
        monkeypatch.setattr(dialogs, "ask_save_path", lambda *args: next(targets))
        card = page.data_card

        card.export_button.click()
        assert (tmp_path / "backup.json").is_file()
        assert "Backup saved and verified" in card.status_label.text()
        card.csv_button.click()
        assert (tmp_path / "transactions.csv").is_file()
        assert "1 transactions exported" in card.status_label.text()

    def test_cancelled_export_writes_nothing(self, page: SettingsPage, tmp_path: Path,
                                             monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(dialogs, "ask_save_path", lambda *args: None)
        page.data_card.export_button.click()
        assert not any(tmp_path.glob("*.json"))
        assert not page.data_card.status_label.isVisible()

    def test_import_asks_first(self, page: SettingsPage, data: AppServices, tmp_path: Path,
                               monkeypatch: pytest.MonkeyPatch) -> None:
        path = tmp_path / "backup.json"
        data.data.export_backup(path)
        data.transactions.create(TransactionDraft(
            data.accounts.list()[0].id, TransactionType.INCOME, "5", fixed_today(),
            data.categories.list(CategoryKind.INCOME)[0].id))
        monkeypatch.setattr(dialogs, "ask_open_path", lambda *args: path)
        questions: list[str] = []
        monkeypatch.setattr(dialogs, "confirm_destructive",
                            lambda parent, title, message, confirm: questions.append(message)
                            or False)

        page.data_card.import_button.click()
        assert "Replace ALL current data" in questions[0] and "1 accounts" in questions[0]
        assert data.balances.total_balance() == Money.of("1005")  # declined: unchanged

        infos: list[str] = []
        monkeypatch.setattr(dialogs, "confirm_destructive", lambda *args: True)
        monkeypatch.setattr(dialogs, "show_info", lambda parent, title, msg: infos.append(msg))
        page.data_card.import_button.click()
        assert data.balances.total_balance() == Money.of("1000")  # the backup's data
        assert "previous data was saved" in infos[0]
        assert page.reloads == [SETTINGS_PAGE_KEY]  # type: ignore[attr-defined]

    def test_invalid_file_is_reported(self, page: SettingsPage, tmp_path: Path,
                                      monkeypatch: pytest.MonkeyPatch) -> None:
        path = tmp_path / "other.json"
        path.write_text("{}", encoding="utf-8")
        monkeypatch.setattr(dialogs, "ask_open_path", lambda *args: path)
        page.data_card.import_button.click()
        assert "not exported by Money Manager" in page.data_card.status_label.text()


class TestReset:
    def test_dialog_needs_the_exact_word(self, qapp: QApplication, data: AppServices) -> None:
        dialog = ResetDialog(data)
        assert not dialog.reset_button.isEnabled() and dialog.cancel_button.isDefault()
        for word in ("reset", "RESET!", "RESE"):
            dialog.confirm_edit.setText(word)
            assert not dialog.reset_button.isEnabled()
        dialog.confirm_edit.setText("RESET")
        assert dialog.reset_button.isEnabled()
        dialog.reset_button.click()
        assert dialog.result() == QDialog.DialogCode.Accepted
        assert dialog.result_info is not None and data.accounts.list() == []
        dialog.deleteLater()

    def test_cancel_keeps_everything(self, page: SettingsPage, data: AppServices,
                                     monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ResetDialog, "exec", lambda self: QDialog.DialogCode.Rejected)
        page.reset_card.reset_button.click()
        assert len(data.accounts.list()) == 1
        assert page.reloads == []  # type: ignore[attr-defined]

    def test_reset_from_the_page(self, page: SettingsPage, data: AppServices,
                                 monkeypatch: pytest.MonkeyPatch) -> None:
        def type_and_confirm(dialog: ResetDialog) -> QDialog.DialogCode:
            dialog.confirm_edit.setText("RESET")
            dialog.confirm()
            return QDialog.DialogCode.Accepted

        infos: list[str] = []
        monkeypatch.setattr(ResetDialog, "exec", type_and_confirm)
        monkeypatch.setattr(dialogs, "show_info", lambda parent, title, msg: infos.append(msg))
        page.reset_card.reset_button.click()
        assert data.accounts.list() == []
        assert "safety backup was saved" in infos[0]
        assert page.reloads == [SETTINGS_PAGE_KEY]  # type: ignore[attr-defined]


def test_window_is_rebuilt_with_the_new_currency(qapp: QApplication, app_config: AppConfig,
                                                 database: Database,
                                                 monkeypatch: pytest.MonkeyPatch) -> None:
    from money_manager.app import WindowManager
    from money_manager.ai.secrets import MemorySecretStore
    from money_manager.services import container

    original_create = container.AppServices.create.__func__  # type: ignore[attr-defined]

    def isolated(cls: type, db: Database, **kwargs: object) -> AppServices:
        kwargs.setdefault("secret_store", MemorySecretStore())
        kwargs.setdefault("environ", {})
        return original_create(cls, db, **kwargs)

    monkeypatch.setattr(container.AppServices, "create", classmethod(isolated))
    manager = WindowManager(app_config, database)
    first = manager.open()
    settings = first.page(SETTINGS_PAGE_KEY)
    assert isinstance(settings, SettingsPage)
    settings.currency_card.combo.setCurrentIndex(settings.currency_card.combo.findData("USD"))
    settings.currency_card.save()

    second = manager.window
    assert second is not None and second is not first
    assert second.current_page.spec.key == SETTINGS_PAGE_KEY
    assert dict(second.page(SETTINGS_PAGE_KEY).about_card.rows)["Currency"] == "USD"  # type: ignore[attr-defined]
    assert not first.isVisible() and second.isVisible()
    second.close()
    second.deleteLater()


class TestCategoryRules:
    def test_add_and_remove(self, page: SettingsPage, app_services: AppServices,
                            monkeypatch: pytest.MonkeyPatch) -> None:
        card = page.rules_card
        assert card.empty_label.isVisibleTo(page) and not card.remove_button.isEnabled()
        app_services.categories.create("Groceries", CategoryKind.EXPENSE)
        monkeypatch.setattr(cards.QInputDialog, "getText",
                            lambda *_a, **_k: ("Carrefour", True))
        monkeypatch.setattr(cards.QInputDialog, "getItem",
                            lambda _p, _t, _l, items, *_a, **_k: (items[0], True))
        card.add_button.click()
        assert [card.list.item(r).text() for r in range(card.list.count())] == [
            "“carrefour” → Groceries  (spending)"]

        card.list.setCurrentRow(0)
        assert card.remove_button.isEnabled()
        card.remove_button.click()
        assert app_services.category_rules.entries() == []
        assert card.empty_label.isVisibleTo(page)

    def test_a_bad_keyword_is_explained(self, page: SettingsPage, app_services: AppServices,
                                        monkeypatch: pytest.MonkeyPatch) -> None:
        app_services.categories.create("Groceries", CategoryKind.EXPENSE)
        monkeypatch.setattr(cards.QInputDialog, "getText", lambda *_a, **_k: ("x", True))
        monkeypatch.setattr(cards.QInputDialog, "getItem",
                            lambda _p, _t, _l, items, *_a, **_k: (items[0], True))
        page.rules_card.add_button.click()
        assert "keyword" in page.rules_card.status_label.text()
