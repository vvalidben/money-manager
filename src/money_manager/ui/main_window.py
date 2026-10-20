"""Main application window: sidebar on the left, page stack on the right."""

import logging

from PySide6.QtCore import QEvent, QObject, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut, QShowEvent
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from money_manager import APP_NAME
from money_manager.core.config import AppConfig
from money_manager.core.errors import MoneyManagerError
from money_manager.domain.recurring import RecordOutcome
from money_manager.domain.reminders import Reminder
from money_manager.services.update_service import UpdateInfo
from money_manager.ui.ai.background import BackgroundCall, run_in_background
from money_manager.services import AppServices
from money_manager.ui.accounts.accounts_page import AccountsPage
from money_manager.ui.advisor.advisor_page import AdvisorPage
from money_manager.ui.allocations.allocations_page import AllocationsPage
from money_manager.ui.budgets.budgets_page import BudgetsPage
from money_manager.ui.components import StatCard
from money_manager.ui.components.toast import Toast
from money_manager.ui.dashboard.dashboard_page import DashboardPage
from money_manager.ui.goals.goals_page import GoalsPage
from money_manager.ui.investments.investments_page import InvestmentsPage
from money_manager.ui.formatting import format_date, format_money
from money_manager.ui.lock.app_lock import AppLock
from money_manager.ui.tray import TrayController
from money_manager.ui.navigation import (
    ICON_PATHS,
    PLUS_PATH,
    SEARCH_PATH,
    SIDEBAR_WIDTH,
    NavItem,
    Sidebar,
    line_icon,
)
from money_manager.ui.pages import (
    ACCOUNTS_PAGE_KEY,
    AI_ADVISOR_PAGE_KEY,
    ALLOCATIONS_PAGE_KEY,
    BUDGETS_PAGE_KEY,
    DASHBOARD_PAGE_KEY,
    DEFAULT_PAGE_KEY,
    GOALS_PAGE_KEY,
    INVESTMENTS_PAGE_KEY,
    PAGES,
    SETTINGS_PAGE_KEY,
    STATISTICS_PAGE_KEY,
    SUBSCRIPTIONS_PAGE_KEY,
    TRANSACTIONS_PAGE_KEY,
    BasePage,
    PageSpec,
    PlaceholderPage,
    SettingsPage,
)
from money_manager.ui.statistics.statistics_page import StatisticsPage
from money_manager.ui.subscriptions.subscriptions_page import SubscriptionsPage
from money_manager.ui.theme import Colors, page_fill
from money_manager.ui.transactions.transactions_page import TransactionsPage
from money_manager.core.i18n import tr

logger = logging.getLogger(__name__)

DEFAULT_WINDOW_SIZE = QSize(1200, 760)
MINIMUM_WINDOW_SIZE = QSize(960, 600)
RECURRING_CHECK_MS = 60 * 60 * 1000  # recurring entries due are recorded hourly
UPDATE_CHECK_DELAY_MS = 8000
REMINDER_DELAY_MS = 15_000  # reminders wait until the window has settled
MAX_REMINDERS_AT_ONCE = 3  # the opt-in update check waits until the window has settled


class MainWindow(QMainWindow):
    # The data behind the services changed (currency, import, reset): the
    # application should rebuild its services and window, then show this page.
    reload_requested = Signal(str)

    def __init__(
        self, config: AppConfig, services: AppServices, parent: QWidget | None = None, *,
        start_locked: bool = False,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(MINIMUM_WINDOW_SIZE)
        self.resize(DEFAULT_WINDOW_SIZE)

        self._pages: dict[str, BasePage] = {}
        self._stack = QStackedWidget()
        for spec in PAGES:
            page = self._create_page(spec, config, services)
            page.navigate_requested.connect(self.show_page)
            page.notice.connect(self._show_notice)
            if isinstance(page, SettingsPage):
                page.reload_requested.connect(self.reload_requested)
                settings_page = page
            self._pages[spec.key] = page
            self._stack.addWidget(page)

        for spec in PAGES:
            self._fill_headline(self._pages[spec.key], spec)

        content_area = QWidget()
        content_area.setObjectName("ContentArea")
        content_area.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(self._stack)

        # The rail is not in the layout: a fixed spacer keeps its place and the
        # rail itself overlays the page when it expands.
        central = QWidget()
        central.setObjectName("ContentArea")
        central.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        rail_space = QWidget()
        rail_space.setFixedWidth(SIDEBAR_WIDTH)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(rail_space)
        layout.addWidget(content_area, 1)
        self.setCentralWidget(central)
        central.installEventFilter(self)

        self.toast = Toast(central)
        self._sidebar = Sidebar([NavItem(spec.key, spec.nav_label) for spec in PAGES], central)
        self._sidebar.page_selected.connect(self.show_page)
        self._global_controls = self._build_global_controls()
        self._controls_host: BasePage | None = None
        self._install_shortcuts()

        # Last, so the lock screen lies above the rail and the notices.
        self.app_lock = AppLock(central, services.settings)
        self.app_lock.locked_changed.connect(self._set_shortcuts_paused)
        self._paused_shortcuts: list[QShortcut] = []
        settings_page.lock_requested.connect(self.lock)
        settings_page.lock_settings_changed.connect(self.app_lock.configure)
        QShortcut(QKeySequence("Ctrl+L"), self, self.lock)

        self.show_page(DEFAULT_PAGE_KEY)
        if start_locked:
            self.app_lock.lock(prompt=True)

        # Recurring entries: dates that have come are recorded once the window is up,
        # then every hour while it stays open (e.g. across midnight).
        self._services = services
        self.recurring_timer = QTimer(self)
        self.recurring_timer.setInterval(RECURRING_CHECK_MS)
        self.recurring_timer.timeout.connect(self.record_recurring)
        self.recurring_timer.timeout.connect(self.check_reminders)
        self.recurring_timer.start()
        QTimer.singleShot(0, self.record_recurring)
        self._update_call: BackgroundCall | None = None
        QTimer.singleShot(UPDATE_CHECK_DELAY_MS, self.check_for_updates)

        # Reminders and the notification-area icon.
        self._quitting = False
        self._told_about_tray = False
        self.tray = TrayController(self)
        self.tray.open_requested.connect(self.open_from_tray)
        self.tray.lock_requested.connect(self.lock)
        self.tray.quit_requested.connect(self.quit_app)
        settings_page.notifications_changed.connect(self.update_tray)
        self.update_tray()
        QTimer.singleShot(REMINDER_DELAY_MS, self.check_reminders)

    def lock(self) -> None:
        self.app_lock.lock()

    def check_for_updates(self) -> None:
        """The opt-in daily check; a newer version is announced with a notice."""
        try:
            if not self._services.updates.due():
                return
        except MoneyManagerError:
            return
        self._update_call = run_in_background(self._services.updates.check,
                                              self._update_checked,
                                              lambda _error: None, owner=self)

    def _update_checked(self, info: UpdateInfo) -> None:
        if info.is_newer:
            self._show_notice(tr("Money Manager {0} is available", info.latest),
                              tr("Settings \u2192 Updates \u2192 Download"))

    def record_recurring(self) -> RecordOutcome | None:
        try:
            outcome = self._services.recurring.record_due()
        except MoneyManagerError as exc:
            logger.warning("Could not record recurring entries: %s", exc)
            return None
        if outcome.recorded:
            count = outcome.recorded
            title = (tr("1 recurring entry recorded") if count == 1
                     else tr("{0} recurring entries recorded", count))
            self._show_notice(title, tr("Transactions → Recurring…"))
        elif outcome.problems:
            problem = outcome.problems[0]
            self._show_notice(tr("A recurring entry could not be recorded"),
                              f"{problem.description}: {problem.message}")
        if outcome.recorded:
            self.current_page.force_refresh()
        return outcome

    def _set_shortcuts_paused(self, locked: bool) -> None:
        """No shortcut reaches the pages under the lock screen."""
        if locked:
            self._paused_shortcuts = [s for s in self.findChildren(QShortcut) if s.isEnabled()]
            for shortcut in self._paused_shortcuts:
                shortcut.setEnabled(False)
        else:
            for shortcut in self._paused_shortcuts:
                shortcut.setEnabled(True)
            self._paused_shortcuts = []

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if watched is self.centralWidget() and event.type() == QEvent.Type.Resize:
            self._sidebar.place(self.centralWidget().height())
            if self.toast.isVisible():
                self.toast.move(self.toast._resting_position())
            if hasattr(self, "app_lock"):
                self.app_lock.place()
        return super().eventFilter(watched, event)

    # ------------------------------------------------------------ global controls

    def _build_global_controls(self) -> QWidget:
        """Search, Ask AI and New entry: shown in the header of whichever page is open."""
        self.global_search = QLineEdit()
        self.global_search.setObjectName("GlobalSearch")
        self.global_search.setPlaceholderText(tr("Search entries"))
        self.global_search.setAccessibleName(tr("Search entries"))
        self.global_search.setToolTip(tr("Search transactions: type and press Enter"))
        self.global_search.setClearButtonEnabled(True)
        self.global_search.setMinimumWidth(180)
        self.global_search.addAction(line_icon(SEARCH_PATH, Colors.TEXT_MUTED, 16),
                                     QLineEdit.ActionPosition.LeadingPosition)
        self.global_search.returnPressed.connect(self.search_entries)

        self.ask_button = QPushButton(tr("Ask AI"))
        self.ask_button.setIcon(line_icon(ICON_PATHS[AI_ADVISOR_PAGE_KEY], Colors.CYAN, 16))
        self.ask_button.setToolTip(tr("Open the AI Advisor"))
        self.ask_button.clicked.connect(self.ask_ai)

        self.new_entry_button = QPushButton(tr("New entry"))
        self.new_entry_button.setObjectName("PrimaryButton")
        self.new_entry_button.setIcon(line_icon(PLUS_PATH, Colors.ON_ACCENT, 16, 2.2))
        self.new_entry_button.setToolTip(tr("Record a transaction"))
        self.new_entry_button.clicked.connect(self.new_entry)

        controls = QWidget()
        row = QHBoxLayout(controls)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.addWidget(self.global_search)
        row.addWidget(self.ask_button)
        row.addWidget(self.new_entry_button)
        return controls

    def _move_global_controls(self, page: BasePage) -> None:
        if self._controls_host is not None and self._controls_host is not page:
            self._controls_host.header.detach(self._global_controls)
        key = page.spec.key
        # Pages with their own search or add button do not repeat them.
        self.global_search.setVisible(key not in (TRANSACTIONS_PAGE_KEY, AI_ADVISOR_PAGE_KEY))
        self.new_entry_button.setVisible(key != TRANSACTIONS_PAGE_KEY)
        self.ask_button.setVisible(key != AI_ADVISOR_PAGE_KEY)
        # One filled button per header: a page's own main action keeps the lime.
        self.new_entry_button.setObjectName(
            "" if page.primary_button is not None else "PrimaryButton")
        self.new_entry_button.setIcon(line_icon(
            PLUS_PATH, Colors.ON_ACCENT if page.primary_button is None else Colors.TEXT, 16, 2.2))
        self.new_entry_button.style().unpolish(self.new_entry_button)
        self.new_entry_button.style().polish(self.new_entry_button)
        if self._controls_host is not page:
            page.header.attach(self._global_controls)
            self._controls_host = page

    def search_entries(self) -> None:
        text = self.global_search.text().strip()
        self.show_page(TRANSACTIONS_PAGE_KEY)
        page = self.current_page
        if page.search_field is not None:
            page.search_field.setText(text)
        page.focus_search()
        self.global_search.clear()

    def ask_ai(self) -> None:
        self.show_page(AI_ADVISOR_PAGE_KEY)
        self.current_page.focus_search()

    def new_entry(self) -> None:
        """Open the transaction dialog; without an account the page shows how to add one."""
        self.show_page(TRANSACTIONS_PAGE_KEY)
        self.current_page.trigger_primary()

    @staticmethod
    def _fill_headline(page: BasePage, spec: PageSpec) -> None:
        """The page's first figure becomes its headline tile, in the page's colour."""
        figures = page.findChildren(StatCard)
        if figures:
            figures[0].set_fill(page_fill(spec.key))

    def _install_shortcuts(self) -> None:
        """Ctrl+1…9 pages · Ctrl+N new item · Ctrl+F search · F5 refresh."""
        for number, spec in enumerate(PAGES[:9], start=1):
            sequence = QKeySequence(f"Ctrl+{number}")
            QShortcut(sequence, self, lambda key=spec.key: self.show_page(key))
            self._sidebar.button(spec.key).setToolTip(
                f"{spec.nav_label} ({sequence.toString(QKeySequence.SequenceFormat.NativeText)})")
        QShortcut(QKeySequence(QKeySequence.StandardKey.New), self,
                  lambda: self.current_page.trigger_primary())
        QShortcut(QKeySequence(QKeySequence.StandardKey.Find), self,
                  lambda: self.current_page.focus_search())
        QShortcut(QKeySequence(QKeySequence.StandardKey.Refresh), self,
                  lambda: self.current_page.force_refresh())

    @property
    def sidebar(self) -> Sidebar:
        return self._sidebar

    @property
    def current_page(self) -> BasePage:
        page = self._stack.currentWidget()
        assert isinstance(page, BasePage)
        return page

    def page(self, key: str) -> BasePage:
        return self._pages[key]

    def show_page(self, key: str) -> None:
        if key not in self._pages:
            raise KeyError(tr("Unknown page: {0!r}", key))
        page = self._pages[key]
        self._stack.setCurrentWidget(page)
        self._sidebar.set_current(key)
        self._move_global_controls(page)
        # Keep keyboard focus in the sidebar on the page now shown, so the focus
        # ring never lingers on the page that was left (shortcut or link navigation).
        focused = QApplication.focusWidget()
        if focused is not None and self._sidebar.isAncestorOf(focused):
            self._sidebar.button(key).setFocus()
        page.on_shown()
        # After the layout has settled: tiles rise in, figures count, bars fill.
        QTimer.singleShot(0, page, page.play_entrance)
        logger.debug("Showing page %s", key)

    # ---------------------------------------------------------- reminders and tray

    def update_tray(self) -> None:
        """The icon shows while reminders or keep-in-tray are on."""
        try:
            settings = self._services.settings
            wanted = settings.reminders_enabled() or settings.keep_in_tray()
        except MoneyManagerError:
            wanted = False
        self.tray.set_visible(wanted)

    def check_reminders(self) -> list[Reminder]:
        """Show the reminders not shown before (as notifications, or in the window)."""
        try:
            due = self._services.reminders.due(format_money, format_date)
        except MoneyManagerError as exc:
            logger.warning("Could not check reminders: %s", exc)
            return []
        shown = due[:MAX_REMINDERS_AT_ONCE]
        for reminder in shown:
            if self.tray.available:
                self.tray.notify(reminder)
        if shown and not self.tray.available and self.isVisible():
            self._show_notice(shown[0].title, shown[0].body)
        try:
            self._services.reminders.mark_shown(due)
        except MoneyManagerError as exc:
            logger.warning("Could not remember the reminders: %s", exc)
        return shown

    def open_from_tray(self, page_key: str) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()
        if page_key:
            self.show_page(page_key)

    def quit_app(self) -> None:
        self._quitting = True
        QApplication.quit()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """With keep-in-tray on, closing hides the window (and locks it when the lock is on)."""
        try:
            keep = self.tray.available and self._services.settings.keep_in_tray()
        except MoneyManagerError:
            keep = False
        if keep and not self._quitting:
            event.ignore()
            self.hide()
            self.app_lock.lock()
            if not self._told_about_tray:
                self._told_about_tray = True
                self.tray.message(tr("Money Manager is still running"),
                                  tr("It keeps reminding you here. Right-click the icon to "
                                     "quit."))
            return
        super().closeEvent(event)

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802
        super().showEvent(event)
        page = self.current_page
        QTimer.singleShot(0, page, page.play_entrance)

    def _show_notice(self, title: str, detail: str) -> None:
        self.toast.show_message(title, detail)

    @staticmethod
    def _create_page(spec: PageSpec, config: AppConfig, services: AppServices) -> BasePage:
        if spec.key == SETTINGS_PAGE_KEY:
            return SettingsPage(spec, config, services)
        if spec.key == TRANSACTIONS_PAGE_KEY:
            return TransactionsPage(spec, services)
        if spec.key == DASHBOARD_PAGE_KEY:
            return DashboardPage(spec, services)
        if spec.key == STATISTICS_PAGE_KEY:
            return StatisticsPage(spec, services)
        if spec.key == GOALS_PAGE_KEY:
            return GoalsPage(spec, services)
        if spec.key == SUBSCRIPTIONS_PAGE_KEY:
            return SubscriptionsPage(spec, services)
        if spec.key == INVESTMENTS_PAGE_KEY:
            return InvestmentsPage(spec, services)
        if spec.key == ACCOUNTS_PAGE_KEY:
            return AccountsPage(spec, services)
        if spec.key == ALLOCATIONS_PAGE_KEY:
            return AllocationsPage(spec, services)
        if spec.key == BUDGETS_PAGE_KEY:
            return BudgetsPage(spec, services)
        if spec.key == AI_ADVISOR_PAGE_KEY:
            return AdvisorPage(spec, services)
        return PlaceholderPage(spec)
