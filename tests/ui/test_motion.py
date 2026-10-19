"""Animations and the design details added with them.

Every animation must end in exactly the state the widget has without motion,
and code (and assistive technology) must only ever see exact figures.
"""

from collections.abc import Iterator
from datetime import date, timedelta

import pytest
from PySide6.QtCore import QAbstractAnimation
from PySide6.QtWidgets import QApplication, QWidget

from money_manager.core.config import AppConfig
from money_manager.domain.enums import CategoryKind
from money_manager.services import AppServices
from money_manager.ui import motion
from money_manager.ui.components import StatCard
from money_manager.ui.components.progress_ring import ProgressRing
from money_manager.ui.components.toast import Toast
from money_manager.ui.dashboard.view_model import renewal_views
from money_manager.ui.main_window import MainWindow
from money_manager.ui.settings.cards import AppearanceCard
from money_manager.ui.theme import IDENTITY_COLORS, Colors, identity_color
from money_manager.ui.transactions.table_model import category_badge
from tests.services.support import fixed_today


@pytest.fixture
def motion_on(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv(motion.MOTION_ENV, "on")
    monkeypatch.setattr(motion, "system_allows", lambda: True)
    motion.set_user_enabled(True)
    yield
    motion.set_user_enabled(True)


@pytest.fixture
def window(qapp: QApplication, app_config: AppConfig,
           app_services: AppServices) -> Iterator[MainWindow]:
    main = MainWindow(app_config, app_services)
    main.resize(1280, 860)
    main.show()
    yield main
    main.close()
    main.deleteLater()


def run_to_end(animation: QAbstractAnimation | None) -> None:
    assert animation is not None
    animation.setCurrentTime(animation.totalDuration())


class TestSwitches:
    def test_off_by_environment_user_or_windows(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(motion, "system_allows", lambda: True)
        monkeypatch.setenv(motion.MOTION_ENV, "off")
        assert not motion.enabled()
        monkeypatch.setenv(motion.MOTION_ENV, "")
        assert motion.enabled()
        motion.set_user_enabled(False)
        try:
            assert not motion.enabled()
        finally:
            motion.set_user_enabled(True)
        monkeypatch.setattr(motion, "system_allows", lambda: False)
        assert not motion.enabled()

    def test_setting_is_stored_and_applied(self, qapp: QApplication,
                                           app_services: AppServices, motion_on: None) -> None:
        assert app_services.settings.animations_enabled() is True
        card = AppearanceCard(app_services)
        card.animations_box.setChecked(False)
        assert app_services.settings.animations_enabled() is False
        assert not motion.user_enabled() and not motion.enabled()
        card.animations_box.setChecked(True)
        assert app_services.settings.animations_enabled() and motion.enabled()
        card.deleteLater()


class TestFigures:
    @pytest.mark.parametrize(("text", "parts"), [
        ("−1,300.00 MAD", ("−", 1300.0, 2, " MAD")),
        ("+5,000.00 MAD", ("+", 5000.0, 2, " MAD")),
        ("74.0%", ("", 74.0, 1, "%")),
        ("1", ("", 1.0, 0, "")),
        ("Streaming", None),
    ])
    def test_split_number(self, text: str, parts: tuple | None) -> None:
        assert motion.split_number(text) == parts

    def test_count_up_ends_exact_and_never_exposes_a_partial_value(
            self, qapp: QApplication, motion_on: None) -> None:
        card = StatCard("Income")
        card.set_value("+5,000.00 MAD", "inflow")
        card.count_up()
        assert card._counting is not None
        card._counting.setCurrentTime(card._counting.duration() // 3)
        assert card.value_label.text() != "+5,000.00 MAD"  # counting on screen…
        assert card.value == "+5,000.00 MAD"  # …but the value is always exact
        assert card.accessibleName() == "Income: +5,000.00 MAD"
        run_to_end(card._counting)
        assert card.value_label.text() == "+5,000.00 MAD"

    def test_a_new_value_stops_the_count(self, qapp: QApplication, motion_on: None) -> None:
        card = StatCard("Income")
        card.set_value("+5,000.00 MAD")
        card.count_up()
        card.set_value("+6,000.00 MAD")
        assert card.value_label.text() == "+6,000.00 MAD" and card._counting is None

    def test_no_count_without_motion(self, qapp: QApplication) -> None:
        card = StatCard("Income")
        card.set_value("+5,000.00 MAD")
        card.count_up()
        assert card._counting is None and card.value_label.text() == "+5,000.00 MAD"


class TestEntrance:
    def test_tiles_rise_in_and_end_untouched(self, window: MainWindow, motion_on: None,
                                             app_services: AppServices) -> None:
        app_services.accounts.create("Bank", opening_balance="100", opening_date=date(2026, 1, 1))
        window.show_page("goals")
        window.show_page("dashboard")
        page = window.current_page
        page.force_refresh()
        QApplication.processEvents()
        before = {id(w): w.geometry() for w in motion.top_level_tiles(page, (StatCard,))}
        page.play_entrance()
        animation = page._entrance
        tiles = animation._targets  # type: ignore[union-attr]
        assert tiles and all(isinstance(t.graphicsEffect(), motion.RiseEffect) for t in tiles)
        motion.finish(animation)
        assert all(t.graphicsEffect() is None for t in tiles)
        after = {id(w): w.geometry() for w in motion.top_level_tiles(page, (StatCard,))}
        assert after == before  # only the painting moved

    def test_still_without_motion(self, window: MainWindow) -> None:
        window.current_page.play_entrance()
        assert window.current_page._entrance is None


class TestRing:
    def test_ring_caps_and_sweeps_to_its_value(self, qapp: QApplication,
                                               motion_on: None) -> None:
        ring = ProgressRing()
        ring.set_progress(1.4, "140.0%", Colors.MINT)
        assert ring.fraction == 1.0 and ring.text == "140.0%"
        assert ring.accessibleName() == "140.0% complete"
        ring.set_progress(0.25, "25.0%", Colors.MINT)
        ring.sweep_in()
        assert ring.shown == 0.0
        run_to_end(ring._animation)
        assert ring.shown == pytest.approx(0.25)
        ring.deleteLater()


class TestToast:
    def test_shows_then_goes(self, window: MainWindow) -> None:
        window._show_notice("Entry added", "+12.00 MAD · Coffee")
        toast = window.toast
        assert toast.isVisible() and toast.message == ("Entry added", "+12.00 MAD · Coffee")
        assert toast.accessibleName() == "Entry added. +12.00 MAD · Coffee"
        host = window.centralWidget()
        assert toast.width() > toast.title_label.sizeHint().width()  # sized to its text
        assert abs(toast.geometry().center().x() - host.width() // 2) <= 1  # bottom centre
        assert host.height() - toast.geometry().bottom() > 0
        toast._timer.timeout.emit()
        assert not toast.isVisible()

    def test_slides_in_with_motion(self, qapp: QApplication, motion_on: None) -> None:
        host = MainWindowHost()
        toast = Toast(host)
        toast.show_message("Entry deleted")
        assert not toast.detail_label.isVisibleTo(toast)
        run_to_end(toast._animation)
        assert toast.pos() == toast._resting_position()
        host.deleteLater()


def MainWindowHost() -> QWidget:  # noqa: N802 - a plain widget to host the toast
    host = QWidget()
    host.resize(800, 600)
    return host


class TestDetails:
    def test_identity_colours_are_stable(self) -> None:
        assert identity_color(None) == Colors.STONE
        assert identity_color(1) == IDENTITY_COLORS[0]
        assert identity_color(1 + len(IDENTITY_COLORS)) == IDENTITY_COLORS[0]

    def test_category_badge_is_cached(self, qapp: QApplication) -> None:
        first = category_badge("G", Colors.MINT)
        assert first is category_badge("G", Colors.MINT) and not first.isNull()

    def test_renewal_wording(self, app_services: AppServices) -> None:
        food = app_services.categories.create("Food", CategoryKind.EXPENSE)
        for name, days in (("Gym", -2), ("Music", 0), ("Cloud", 1), ("Phone", 5)):
            app_services.subscriptions.create(
                name, amount="10", frequency="monthly",
                next_payment_date=fixed_today() + timedelta(days=days), category_id=food.id)
        views = renewal_views(app_services.subscriptions.upcoming(), limit=4)
        assert [(v.name, v.when, v.overdue) for v in views] == [
            ("Gym", "Overdue by 2 days", True), ("Music", "Today", False),
            ("Cloud", "Tomorrow", False), ("Phone", "In 5 days", False),
        ]
        assert views[0].day == str((fixed_today() - timedelta(days=2)).day)

    def test_dashboard_lists_renewals(self, window: MainWindow,
                                      app_services: AppServices) -> None:
        app_services.accounts.create("Bank", opening_balance="100", opening_date=date(2026, 1, 1))
        food = app_services.categories.create("Food", CategoryKind.EXPENSE)
        app_services.subscriptions.create("Streaming", amount="65", frequency="monthly",
                                          next_payment_date=fixed_today() + timedelta(days=3),
                                          category_id=food.id)
        page = window.current_page
        page.force_refresh()
        card = page.renewing_card  # type: ignore[attr-defined]
        assert [(r.name, r.when, r.amount) for r in card.rows] == [
            ("Streaming", "In 3 days", "65.00 MAD")]
        assert not card.empty_label.isVisibleTo(card)

    def test_nav_highlight_follows_the_page(self, window: MainWindow) -> None:
        window.show_page("goals")
        QApplication.processEvents()
        indicator = window.sidebar._indicator
        assert indicator.property("fill") == "mint"
        assert indicator.geometry() == window.sidebar.button("goals").geometry()


class TestFigureFit:
    def test_long_figures_step_down_instead_of_being_clipped(self, qapp: QApplication) -> None:
        card = StatCard("Income this month")
        card.resize(420, 120)
        card.set_value("+5.00 MAD")
        assert card.value_label.property("fit") == ""
        card.resize(230, 120)
        card.set_value("+14,500.00 MAD")
        assert card.value_label.property("fit") in ("m", "s", "xs")
        assert card.value == "+14,500.00 MAD"  # the text itself is never shortened
        card.deleteLater()
