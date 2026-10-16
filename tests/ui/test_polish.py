"""UI consistency: theme tokens, header actions, empty states, keyboard use, accessibility."""

import re
from collections.abc import Iterator
from datetime import date

import pytest
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication

from money_manager.core.config import AppConfig
from money_manager.domain.enums import CategoryKind
from money_manager.services import AppServices
from money_manager.ui.components import EmptyState, StatCard
from money_manager.ui.main_window import MainWindow
from money_manager.ui.pages import PAGES
from money_manager.ui.theme import Colors, FontSize, build_stylesheet


@pytest.fixture
def window(qapp: QApplication, app_config: AppConfig,
           app_services: AppServices) -> Iterator[MainWindow]:
    main = MainWindow(app_config, app_services)
    main.resize(1280, 860)
    main.show()
    yield main
    main.close()
    main.deleteLater()


def shortcut(window: MainWindow, keys: str) -> QShortcut:
    wanted = QKeySequence(keys)
    return next(s for s in window.findChildren(QShortcut) if s.key() == wanted)


class TestTheme:
    def test_font_sizes_come_from_the_type_scale(self) -> None:
        scale = {value for name, value in vars(FontSize).items() if name.isupper()}
        used = {int(size) for size in re.findall(r"font-size:\s*(\d+)px", build_stylesheet())}
        assert used <= scale

    def test_colours_come_from_the_tokens(self) -> None:
        tokens = {value.upper() for name, value in vars(Colors).items()
                  if name.isupper() and value.startswith("#")} | {"#FFFFFF"}
        used = {colour.upper() for colour in re.findall(r"#[0-9A-Fa-f]{6}\b", build_stylesheet())}
        assert used <= tokens

    def test_keyboard_focus_is_visible(self) -> None:
        sheet = build_stylesheet()
        for selector in ("QPushButton:focus", "#PrimaryButton:focus", "#NavButton:focus",
                         "QLineEdit:focus", "QTableView:focus", "QCheckBox:focus"):
            assert selector in sheet


class TestHeaderActions:
    def test_primary_actions_sit_in_the_page_header(self, window: MainWindow,
                                                     app_services: AppServices) -> None:
        app_services.accounts.create("Bank", opening_balance="10", opening_date=date(2026, 1, 1))
        for key in ("transactions", "goals", "subscriptions", "investments"):
            window.show_page(key)
            page = window.current_page
            assert page.primary_button is not None
            assert page.header.isAncestorOf(page.primary_button)

    def test_empty_pages_offer_a_single_call_to_action(self, window: MainWindow) -> None:
        for key in ("goals", "subscriptions", "investments"):
            window.show_page(key)
            page = window.current_page
            assert page.empty_state.isVisible()  # type: ignore[attr-defined]
            assert not page.primary_button.isVisible()  # type: ignore[union-attr]
            assert not page.trigger_primary()

    def test_the_header_action_returns_with_data(self, window: MainWindow,
                                                 app_services: AppServices) -> None:
        app_services.goals.create_manual("Trip", target="1000")
        window.show_page("goals")
        assert window.current_page.primary_button.isVisible()  # type: ignore[union-attr]

    def test_transactions_without_an_account_show_only_the_empty_state(
        self, window: MainWindow, app_services: AppServices,
    ) -> None:
        window.show_page("transactions")
        page = window.current_page
        hidden = (page.summary_row, page.filter_bar, page.footer,  # type: ignore[attr-defined]
                  page.add_button)  # type: ignore[attr-defined]
        assert page.showing_empty_state and not any(w.isVisible() for w in hidden)  # type: ignore[attr-defined]

        app_services.accounts.create("Bank", opening_balance="10", opening_date=date(2026, 1, 1))
        page.force_refresh()
        assert all(w.isVisible() for w in hidden)


class TestKeyboard:
    def test_ctrl_number_opens_pages(self, window: MainWindow) -> None:
        for number, spec in enumerate(PAGES[:9], start=1):
            shortcut(window, f"Ctrl+{number}").activated.emit()
            assert window.current_page.spec.key == spec.key
            assert f"Ctrl+{number}" in window.sidebar.button(spec.key).toolTip()

    def test_ctrl_n_runs_the_primary_action(self, window: MainWindow,
                                            app_services: AppServices) -> None:
        app_services.goals.create_manual("Trip", target="1000")
        window.show_page("goals")
        clicks: list[bool] = []
        window.current_page.primary_button.clicked.connect(  # type: ignore[union-attr]
            lambda: clicks.append(True))
        window.current_page.primary_button.clicked.disconnect(  # type: ignore[union-attr]
            window.current_page.create_goal)  # type: ignore[attr-defined]  # no modal dialog
        shortcut(window, QKeySequence(QKeySequence.StandardKey.New).toString()).activated.emit()
        assert clicks == [True]

    def test_ctrl_f_focuses_the_search(self, window: MainWindow,
                                       app_services: AppServices) -> None:
        app_services.accounts.create("Bank", opening_balance="10", opening_date=date(2026, 1, 1))
        window.show_page("transactions")
        page = window.current_page
        page.search_field.setText("coffee")  # type: ignore[union-attr]
        assert page.focus_search()
        assert page.search_field.selectedText() == "coffee"  # type: ignore[union-attr]
        window.show_page("dashboard")
        assert not window.current_page.focus_search()  # nothing to search there

    def test_f5_refreshes_even_without_changes(self, window: MainWindow,
                                               app_services: AppServices) -> None:
        window.show_page("goals")
        refreshed: list[bool] = []
        page = window.current_page
        original = page.refresh  # type: ignore[attr-defined]

        def spy() -> None:
            refreshed.append(True)
            original()

        page.refresh = spy  # type: ignore[attr-defined, method-assign]
        page.on_shown()
        assert refreshed == []  # nothing changed: skipped
        shortcut(window, QKeySequence(QKeySequence.StandardKey.Refresh).toString()).activated.emit()
        assert refreshed == [True]


class TestAccessibility:
    def test_stat_cards_announce_label_and_value(self, qapp: QApplication) -> None:
        card = StatCard("Total balance")
        card.set_value("38,559.00 MAD")
        card.set_caption("As of 27 Sep 2026")
        assert card.accessibleName() == "Total balance: 38,559.00 MAD"
        assert card.accessibleDescription() == "As of 27 Sep 2026"

    def test_empty_states_are_named_and_centred(self, qapp: QApplication) -> None:
        state = EmptyState("No goals yet", "Create a goal.", badge=None, action_text="Create")
        assert state.accessibleName() == "No goals yet"
        assert state.heading_label.alignment() & state.heading_label.alignment().AlignHCenter

    def test_filter_controls_have_names(self, window: MainWindow,
                                        app_services: AppServices) -> None:
        app_services.accounts.create("Bank", opening_balance="10", opening_date=date(2026, 1, 1))
        app_services.categories.create("Food", CategoryKind.EXPENSE)
        window.show_page("transactions")
        bar = window.current_page.filter_bar  # type: ignore[attr-defined]
        for widget in (bar.search_edit, bar.period_combo, bar.type_combo, bar.category_combo,
                       bar.account_combo):
            assert widget.accessibleName()

    def test_navigation_buttons_are_named(self, window: MainWindow) -> None:
        for spec in PAGES:
            assert window.sidebar.button(spec.key).accessibleName() == spec.nav_label
