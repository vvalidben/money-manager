"""The light theme: tokens, the stylesheet, and choosing it in Settings."""

import re
from collections.abc import Iterator

import pytest
from PySide6.QtWidgets import QApplication

from money_manager.core.errors import ValidationError
from money_manager.services import AppServices
from money_manager.ui import theme
from money_manager.ui.settings import cards
from money_manager.ui.settings.cards import AppearanceCard
from money_manager.ui.theme import Colors, build_stylesheet, resolve_palette, use_palette


@pytest.fixture
def light() -> Iterator[None]:
    use_palette("light")
    yield
    use_palette("dark")


def test_settings_default_and_choices(app_services: AppServices) -> None:
    assert app_services.settings.theme() == "dark"
    for choice in ("light", "system", "dark"):
        assert app_services.settings.set_theme(choice) == choice
        assert app_services.settings.theme() == choice
    with pytest.raises(ValidationError):
        app_services.settings.set_theme("purple")


def test_switching_palettes_and_back(light: None) -> None:
    assert theme.current_palette() == "light"
    assert Colors.CONTENT_BG == "#F3F3EF" and Colors.TEXT == "#16181D"
    assert Colors.ACCENT == "#C8F169"  # the accent and pastels stay
    use_palette("dark")
    assert Colors.CONTENT_BG == "#0C0D10" and Colors.TEXT == "#F2F2EF"
    with pytest.raises(ValueError):
        use_palette("sepia")


def test_light_stylesheet_uses_only_tokens(light: None) -> None:
    tokens = {value.upper() for name, value in vars(Colors).items()
              if name.isupper() and value.startswith("#")} | {"#FFFFFF"}
    used = {c.upper() for c in re.findall(r"#[0-9A-Fa-f]{6}\b", build_stylesheet())}
    assert used <= tokens
    assert "#0C0D10" not in used  # no dark ground left behind


def test_system_follows_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(theme, "windows_prefers_light", lambda: True)
    assert resolve_palette("system") == "light"
    monkeypatch.setattr(theme, "windows_prefers_light", lambda: False)
    assert resolve_palette("system") == "dark"
    assert resolve_palette("light") == "light" and resolve_palette("odd") == "dark"


def test_card_offers_a_restart(qapp: QApplication, app_services: AppServices,
                               monkeypatch: pytest.MonkeyPatch) -> None:
    card = AppearanceCard(app_services)
    card.show()
    try:
        assert card.theme_combo.currentData() == "dark" and card.restart_button.isHidden()
        card.theme_combo.setCurrentIndex(card.theme_combo.findData("light"))
        assert app_services.settings.theme() == "light"
        assert card.restart_button.isVisible()
        restarts: list[bool] = []
        monkeypatch.setattr(cards, "restart_application", lambda: restarts.append(True))
        card.restart_button.click()
        assert restarts == [True]
        card.theme_combo.setCurrentIndex(card.theme_combo.findData("dark"))
        assert card.restart_button.isHidden()
    finally:
        card.close()
