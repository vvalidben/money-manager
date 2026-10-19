from collections.abc import Iterator
from datetime import date

import pytest
from PySide6.QtWidgets import QApplication

from money_manager import APP_NAME
from money_manager.core.config import AppConfig
from money_manager.services import AppServices
from money_manager.ui.components import StatCard
from money_manager.ui.main_window import MainWindow
from money_manager.ui.pages import DEFAULT_PAGE_KEY, PAGES, SETTINGS_PAGE_KEY, SettingsPage
from money_manager.ui.theme import PAGE_FILLS, page_fill

EXPECTED_SECTIONS = [
    "dashboard",
    "accounts",
    "transactions",
    "budgets",
    "allocations",
    "goals",
    "subscriptions",
    "investments",
    "statistics",
    "ai_advisor",
    "settings",
]


@pytest.fixture
def window(
    qapp: QApplication, app_config: AppConfig, app_services: AppServices
) -> Iterator[MainWindow]:
    main_window = MainWindow(app_config, app_services)
    main_window.show()
    yield main_window
    main_window.close()
    main_window.deleteLater()


def test_window_title(window: MainWindow) -> None:
    assert window.windowTitle() == APP_NAME


def test_sidebar_lists_every_section(window: MainWindow) -> None:
    assert sorted(window.sidebar.keys()) == sorted(EXPECTED_SECTIONS)
    assert [spec.key for spec in PAGES] == EXPECTED_SECTIONS


def test_every_page_has_a_colour_icon_and_headline_tile(window: MainWindow) -> None:
    assert set(PAGE_FILLS) == set(EXPECTED_SECTIONS)
    for spec in PAGES:
        button = window.sidebar.button(spec.key)
        assert button.property("page") == spec.key and not button.icon().isNull()
        figures = window.page(spec.key).findChildren(StatCard)
        if figures:
            assert figures[0].fill == page_fill(spec.key)
            assert all(figure.fill is None for figure in figures[1:])


def test_the_rail_shows_labels_only_when_expanded(window: MainWindow) -> None:
    rail = window.sidebar
    assert not rail.expanded and rail.button("goals").text() == ""
    assert rail.button("goals").accessibleName() == "Goals"
    rail.set_expanded(True)
    assert rail.button("goals").text() == "Goals"
    rail.set_expanded(False)
    rail._animation.setCurrentTime(rail._animation.duration())  # finish at once
    assert rail.button("goals").text() == ""


def test_global_controls_follow_the_page(window: MainWindow) -> None:
    for key in ("dashboard", "goals", "settings"):
        window.show_page(key)
        assert window.page(key).header.isAncestorOf(window.new_entry_button)
        assert window.new_entry_button.isVisible() and window.global_search.isVisible()
    window.show_page("transactions")  # the page has its own search and add button
    assert not window.new_entry_button.isVisible() and not window.global_search.isVisible()


def test_global_search_and_ask_ai_open_their_pages(window: MainWindow,
                                                   app_services: AppServices) -> None:
    app_services.accounts.create("Bank", opening_balance="10", opening_date=date(2026, 1, 1))
    window.show_page("goals")
    window.global_search.setText("rent")
    window.search_entries()
    page = window.current_page
    assert page.spec.key == "transactions" and page.search_field.text() == "rent"  # type: ignore[union-attr]
    assert window.global_search.text() == ""
    window.ask_ai()
    assert window.current_page.spec.key == "ai_advisor"


def test_starts_on_dashboard(window: MainWindow) -> None:
    assert window.current_page.spec.key == DEFAULT_PAGE_KEY
    assert window.sidebar.current_key() == DEFAULT_PAGE_KEY


@pytest.mark.parametrize("key", EXPECTED_SECTIONS)
def test_clicking_nav_button_switches_page(window: MainWindow, key: str) -> None:
    window.sidebar.button(key).click()

    assert window.current_page.spec.key == key
    assert window.sidebar.current_key() == key


def test_show_page_updates_sidebar(window: MainWindow) -> None:
    window.show_page("goals")

    assert window.sidebar.current_key() == "goals"
    assert window.sidebar.button("goals").isChecked()
    assert not window.sidebar.button(DEFAULT_PAGE_KEY).isChecked()


def test_show_unknown_page_raises(window: MainWindow) -> None:
    with pytest.raises(KeyError):
        window.show_page("does_not_exist")


def test_every_page_shows_its_title(window: MainWindow) -> None:
    for spec in PAGES:
        page = window.page(spec.key)
        assert page.header.title_label.text() == spec.title
        if spec.key == DEFAULT_PAGE_KEY:
            # The dashboard replaces its subtitle with the period it reports on.
            assert "month to date" in page.header.subtitle_label.text()
        else:
            assert page.header.subtitle_label.text() == spec.subtitle


def test_settings_page_shows_local_storage_location(
    window: MainWindow, app_config: AppConfig
) -> None:
    page = window.page(SETTINGS_PAGE_KEY)

    assert isinstance(page, SettingsPage)
    texts = {label.text() for label in page.findChildren(type(page.header.title_label))}
    assert str(app_config.database_path) in texts
    assert "MAD" in texts
