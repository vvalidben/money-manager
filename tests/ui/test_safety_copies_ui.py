"""Settings → Safety copies: list, restore after confirmation, refuse unreadable copies."""

from datetime import date

import pytest
from PySide6.QtWidgets import QApplication

from money_manager.core.config import AppConfig
from money_manager.domain.money import Money
from money_manager.services import AppServices
from money_manager.services.data_service import RESET_CONFIRMATION
from money_manager.ui import dialogs
from money_manager.ui.settings.cards import SafetyCopiesCard


@pytest.fixture
def reset_once(app_services: AppServices) -> AppServices:
    app_services.accounts.create("Bank", opening_balance="10210", opening_date=date(2026, 1, 1))
    app_services.data.reset(RESET_CONFIRMATION)
    return app_services


def test_lists_and_restores_after_confirmation(qapp: QApplication, app_config: AppConfig,
                                               reset_once: AppServices,
                                               monkeypatch: pytest.MonkeyPatch) -> None:
    card = SafetyCopiesCard(reset_once, app_config)
    assert card.list.count() == 1
    assert card.list.item(0).text().startswith("Before a reset · ")
    assert card.list.item(0).text().endswith("1 account, 0 transactions")
    assert card.restore_button.isEnabled()

    asked: list[str] = []
    monkeypatch.setattr(dialogs, "confirm_destructive",
                        lambda _parent, _title, message, *_a: asked.append(message) or True)
    monkeypatch.setattr(dialogs, "show_info", lambda *_args: None)
    changed: list[bool] = []
    card.changed.connect(lambda: changed.append(True))
    card.restore_button.click()

    assert "Replace ALL current data" in asked[0]
    assert changed == [True]
    assert reset_once.balances.total_balance() == Money.of("10210")
    card.deleteLater()


def test_cancel_changes_nothing(qapp: QApplication, app_config: AppConfig,
                                reset_once: AppServices,
                                monkeypatch: pytest.MonkeyPatch) -> None:
    card = SafetyCopiesCard(reset_once, app_config)
    monkeypatch.setattr(dialogs, "confirm_destructive", lambda *_args: False)
    card.restore_button.click()
    assert reset_once.accounts.list() == []
    card.deleteLater()


def test_unreadable_copies_cannot_be_restored(qapp: QApplication, app_config: AppConfig,
                                              app_services: AppServices) -> None:
    broken = app_config.database_path.with_name(
        "money_manager.backup-before-import-20260101T000000Z.db")
    broken.write_bytes(b"garbage")
    card = SafetyCopiesCard(app_services, app_config)
    assert card.list.item(0).text().endswith("cannot be read")
    assert not card.restore_button.isEnabled()
    card.deleteLater()


def test_no_copies_yet(qapp: QApplication, app_config: AppConfig,
                       app_services: AppServices) -> None:
    card = SafetyCopiesCard(app_services, app_config)
    assert card.list.isHidden() and not card.empty_label.isHidden()
    assert not card.restore_button.isEnabled()
    card.deleteLater()
