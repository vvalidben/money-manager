"""AI Advisor page.

The financial summary at the top comes from the deterministic engine
(``FinancialAnalysisService``) and works with AI off, unavailable or failing.
AI answers interpret those figures; they are requested on a worker thread,
online requests only after the user has reviewed and confirmed exactly what
is sent, and every answer is kept in the local insight history.
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from functools import partial

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from money_manager.ai.prompts import MAX_QUESTION_LENGTH, AIResponse
from money_manager.ai.providers.anthropic_provider import API_HOST
from money_manager.ai.settings import MODE_LABELS, AIMode, AISettings
from money_manager.ai.verification import unsupported_numbers
from money_manager.core.errors import AIDisabledError, MoneyManagerError
from money_manager.domain.financial_analysis import FinancialAnalysis
from money_manager.domain.insights import (
    KIND_LABELS,
    PERIOD_LABELS,
    AdvisorPeriod,
    Insight,
    InsightKind,
    advisor_range,
)
from money_manager.domain.periods import DateRange
from money_manager.services import AppServices, PreparedRequest
from money_manager.ui import dialogs
from money_manager.ui.accounts.account_dialog import AccountDialog
from money_manager.ui.ai import consent_dialog
from money_manager.ui.ai.background import BackgroundCall, run_in_background
from money_manager.ui.components import (
    AdaptiveRow,
    Card,
    EmptyState,
    FlowRow,
    ResponsiveRow,
    StatCard,
    compact_combo,
)
from money_manager.ui.components.facts_card import FactsCard
from money_manager.ui.formatting import format_date, format_percent, format_signed_money, month_abbreviation
from money_manager.ui.pages.base_page import BasePage
from money_manager.ui.pages.registry import SETTINGS_PAGE_KEY, PageSpec
from money_manager.ui.theme import SIDE_BY_SIDE_MIN_WIDTH, Spacing
from money_manager.core.i18n import tr

logger = logging.getLogger(__name__)

TASK_BUTTONS = (InsightKind.INSIGHTS, InsightKind.SUGGESTIONS, InsightKind.SPENDING,
                InsightKind.MONTHLY)
DISCLAIMER = (tr("AI answers interpret the figures calculated above and can be wrong. Numbers in "
              "the answer are checked against your data; check anything important yourself."))


def mode_notice(settings: AISettings, has_key: bool) -> tuple[str, bool]:
    """(text, is_online) describing where the data goes in the current mode."""
    match settings.mode:
        case AIMode.LOCAL:
            return (tr("Local AI ({0} via Ollama): your financial summary is processed on this "
                       "computer and is not sent over the internet.", settings.local_model)), False
        case AIMode.ONLINE:
            key = "" if has_key else tr(" Add an Anthropic API key in Settings first.")
            return (tr("Online AI ({0}, Anthropic): each request sends a summary of your "
                       "finances to {1}. You will see exactly what is sent and nothing leaves "
                       "this computer until you confirm.{2}", settings.online_model, API_HOST, key)), True
        case AIMode.AUTO:
            local = (tr("the local model ({0}) when Ollama is running", settings.local_model)
                     if settings.local_model else tr("no local model (none chosen)"))
            return (tr("Automatic: uses {0}; otherwise the online provider ({1}) at {2}. "
                       "Processing stays on this computer with the local model; online requests "
                       "show what would be sent and wait for your confirmation.", local, settings.online_model, API_HOST)), True
        case _:
            return (tr("AI is off. The financial summary below is calculated by Money Manager "
                    "without AI; choose a local or online provider to get AI insights.")), False


def local_time(value: datetime) -> datetime:
    """Stored timestamps are UTC (SQLite CURRENT_TIMESTAMP)."""
    aware = value if value.tzinfo else value.replace(tzinfo=UTC)
    return aware.astimezone()


def period_text(period: DateRange) -> str:
    return f"{format_date(period.start)} – {format_date(period.end)}"


class AdvisorPage(BasePage):
    def __init__(self, spec: PageSpec, services: AppServices, parent: QWidget | None = None) -> None:
        super().__init__(spec, parent, fill=True)
        self._services = services
        self._ai = services.ai
        self.analysis: FinancialAnalysis | None = None
        self.current: Insight | None = None
        self._call: BackgroundCall | None = None

        # Filter row
        self.period_combo = QComboBox()
        for value, label in PERIOD_LABELS.items():
            self.period_combo.addItem(tr(label), value.value)
        self.period_combo.currentIndexChanged.connect(self.refresh_summary)
        self.provider_combo = QComboBox()
        for mode, label in MODE_LABELS.items():
            self.provider_combo.addItem(tr(label), mode.value)
        self.provider_combo.currentIndexChanged.connect(self._provider_chosen)
        self.refresh_button = QPushButton(tr("Refresh"))
        self.refresh_button.setToolTip(tr("Recalculate the summary from your latest data."))
        self.refresh_button.clicked.connect(self.refresh)
        self.settings_button = QPushButton(tr("AI settings…"))
        self.settings_button.clicked.connect(
            lambda: self.navigate_requested.emit(SETTINGS_PAGE_KEY))
        compact_combo(self.period_combo, 12)
        compact_combo(self.provider_combo, 18)
        period_label = QLabel(tr("Period"))
        period_label.setBuddy(self.period_combo)
        provider_label = QLabel(tr("AI provider"))
        provider_label.setBuddy(self.provider_combo)
        self.period_combo.setAccessibleName(tr("Period"))
        self.provider_combo.setAccessibleName(tr("AI provider"))
        filter_row = FlowRow([_pair(period_label, self.period_combo),
                              _pair(provider_label, self.provider_combo)])
        self.header.add_action(self.refresh_button)
        self.header.add_action(self.settings_button)

        self.mode_notice = QLabel()
        self.mode_notice.setWordWrap(True)

        # Deterministic summary (no AI)
        # Keyed by the English name; each card shows it in the interface language.
        self.stat_cards = {name: StatCard(tr(name), compact=True)
                           for name in ("Income", "Expenses", "Savings rate", "Net change")}
        self.facts_card = FactsCard(
            tr("Financial summary"),
            tr("Calculated by Money Manager's fixed rules — available with or without AI."))

        # AI panel
        self.ai_card = Card(tr("Ask the advisor"))
        self.task_buttons = {kind: QPushButton(tr(KIND_LABELS[kind])) for kind in TASK_BUTTONS}
        task_row = FlowRow()
        for kind, button in self.task_buttons.items():
            button.clicked.connect(partial(self.run_task, kind))
            task_row.add(button)
        self.question_edit = QLineEdit()
        self.question_edit.setMaxLength(MAX_QUESTION_LENGTH)
        self.question_edit.setPlaceholderText(tr("Ask about your finances, e.g. Why did my spending "
                                              "rise this month?"))
        self.question_edit.returnPressed.connect(self.ask)
        self.question_edit.setAccessibleName(tr("Question for the advisor"))
        self.search_field = self.question_edit
        self.ask_button = QPushButton(tr("Ask"))
        self.ask_button.setObjectName("PrimaryButton")
        self.ask_button.clicked.connect(self.ask)
        question_row = QHBoxLayout()
        question_row.addWidget(self.question_edit, 1)
        question_row.addWidget(self.ask_button)
        self.status_label = QLabel()
        self.status_label.setObjectName("MutedLabel")
        self.status_label.setWordWrap(True)
        self.status_label.hide()

        self.answer_title = QLabel()
        self.answer_title.setObjectName("CardHeading")
        self.answer_meta = QLabel()
        self.answer_meta.setObjectName("MutedLabel")
        self.answer_meta.setWordWrap(True)
        self.answer_view = QTextBrowser()
        self.answer_view.setOpenLinks(False)
        self.answer_view.setOpenExternalLinks(False)
        self.answer_view.setMinimumHeight(260)
        self.answer_view.setAccessibleName(tr("Advisor answer"))
        self.number_warning = QLabel()
        self.number_warning.setObjectName("CautionNotice")
        self.number_warning.setWordWrap(True)
        self.number_warning.hide()
        disclaimer = QLabel(DISCLAIMER)
        disclaimer.setObjectName("MutedLabel")
        disclaimer.setWordWrap(True)
        self.regenerate_button = QPushButton(tr("Regenerate"))
        self.regenerate_button.setToolTip(tr("Ask again for the same period with your latest data."))
        self.regenerate_button.clicked.connect(self.regenerate)
        self.sent_button = QPushButton(tr("What the AI received"))
        self.sent_button.clicked.connect(self.show_context)
        answer_buttons = QHBoxLayout()
        answer_buttons.addWidget(self.regenerate_button)
        answer_buttons.addWidget(self.sent_button)
        answer_buttons.addStretch(1)
        self.answer_box = QWidget()
        answer_layout = QVBoxLayout(self.answer_box)
        answer_layout.setContentsMargins(0, Spacing.SM, 0, 0)
        answer_layout.setSpacing(Spacing.SM)
        for widget in (self.answer_title, self.answer_meta, self.answer_view,
                       self.number_warning, disclaimer):
            answer_layout.addWidget(widget)
        answer_layout.addLayout(answer_buttons)
        self.answer_box.hide()

        self.ai_card.body.addWidget(task_row)
        self.ai_card.body.addLayout(question_row)
        self.ai_card.body.addWidget(self.status_label)
        self.ai_card.body.addWidget(self.answer_box)
        self.ai_card.body.addStretch(1)  # content stays at the top when the row is taller

        # History
        self.history_card = Card(tr("Insight history"))
        history_note = QLabel(tr("Stored only in your local database."))
        history_note.setObjectName("MutedLabel")
        self.history_list = QListWidget()
        self.history_list.setMinimumHeight(260)
        self.history_list.setAccessibleName(tr("Insight history"))
        self.history_list.currentItemChanged.connect(self._history_selected)
        self.delete_button = QPushButton(tr("Delete"))
        self.delete_button.clicked.connect(self.delete_selected)
        self.clear_button = QPushButton(tr("Clear history"))
        self.clear_button.clicked.connect(self.clear_history)
        history_buttons = QHBoxLayout()
        history_buttons.addWidget(self.delete_button)
        history_buttons.addWidget(self.clear_button)
        history_buttons.addStretch(1)
        self.history_card.body.addWidget(history_note)
        self.history_card.body.addWidget(self.history_list, 1)
        self.history_card.body.addLayout(history_buttons)

        self.empty_state = EmptyState(
            tr("Create an account to get started"),
            tr("The advisor explains figures calculated from your recorded transactions. Add the "
            "account you want to track first."),
            badge=None, action_text=tr("Create account"))
        self.empty_state.action_clicked.connect(self.create_account)

        grid = QGridLayout()
        grid.setHorizontalSpacing(Spacing.MD)
        grid.setVerticalSpacing(Spacing.MD)
        grid.addWidget(ResponsiveRow(tuple(self.stat_cards.values()), min_item_width=170),
                       0, 0, 1, 12)
        grid.addWidget(self.facts_card, 1, 0, 1, 12)
        self.ask_row = AdaptiveRow([(self.ai_card, 8), (self.history_card, 4)], SIDE_BY_SIDE_MIN_WIDTH)
        grid.addWidget(self.ask_row, 2, 0, 1, 12)
        for column in range(12):
            grid.setColumnStretch(column, 1)
        self._grid = QWidget()
        self._grid.setLayout(grid)

        content = QWidget()
        content.setObjectName("TransparentArea")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, Spacing.SM, 0)
        content_layout.addWidget(self.empty_state)
        content_layout.addWidget(self._grid)
        content_layout.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(content)

        self.add_content(filter_row)
        self.add_content(self.mode_notice)
        self.add_content(scroll, stretch=1)

    # ------------------------------------------------------------ public API

    def on_shown(self) -> None:
        # The provider status is cheap and may change outside the database (API key).
        self._load_provider()
        # The summary and history only change with the data: skip them if nothing changed.
        if self.already_current(self._services.freshness()):
            return
        self.refresh_summary()
        self.reload_history()

    @property
    def period(self) -> DateRange:
        return advisor_range(AdvisorPeriod(self.period_combo.currentData()),
                             self._services.today())

    @property
    def busy(self) -> bool:
        return self._call is not None and self._call.running

    def refresh(self) -> None:
        self._load_provider()
        self.refresh_summary()
        self.reload_history()

    def refresh_summary(self) -> None:
        try:
            analysis = self._services.analysis.analyze(self.period)
        except MoneyManagerError as exc:
            logger.warning("Could not compute the advisor summary: %s", exc)
            dialogs.show_warning(self, tr("Could not compute the summary"), str(exc))
            return
        self.analysis = analysis
        self.empty_state.setVisible(not analysis.has_accounts)
        self._grid.setVisible(analysis.has_accounts)
        totals = analysis.totals
        values = {
            "Income": (format_signed_money(totals.income), "inflow"),
            "Expenses": (format_signed_money(-totals.expenses), "outflow"),
            "Savings rate": ("—" if analysis.savings_rate is None
                             else format_percent(analysis.savings_rate), "neutral"),
            "Net change": (format_signed_money(totals.net_change),
                           "outflow" if totals.net_change.is_negative() else "neutral"),
        }
        for name, (text, tone) in values.items():
            self.stat_cards[name].set_value(text, tone)
            self.stat_cards[name].set_caption(period_text(analysis.period))
        self.facts_card.set_facts([fact.text for fact in analysis.facts])
        self._update_actions()

    def reload_history(self) -> None:
        selected = self.current.id if self.current else None
        try:
            insights = self._ai.history()
        except MoneyManagerError as exc:
            self._show_status(str(exc), error=True)
            return
        self.history_list.blockSignals(True)
        self.history_list.clear()
        for insight in insights:
            created = local_time(insight.created_at)
            item = QListWidgetItem(f"{created.day:02d} {month_abbreviation(created)} "
                                   f"{created:%H:%M} · {insight.title}")
            item.setToolTip(f"{period_text(insight.period)} · {insight.provider} {insight.model}")
            item.setData(Qt.ItemDataRole.UserRole, insight.id)
            self.history_list.addItem(item)
            if insight.id == selected:
                self.history_list.setCurrentItem(item)
        self.history_list.blockSignals(False)
        self._update_actions()

    # --------------------------------------------------------------- asking

    def run_task(self, kind: InsightKind) -> None:
        self._start(lambda: self._ai.prepare(kind=kind, period=self.period))

    def ask(self) -> None:
        question = self.question_edit.text()
        self._start(lambda: self._ai.prepare(question, kind=InsightKind.QUESTION,
                                             period=self.period))

    def regenerate(self) -> None:
        insight = self.current
        if insight is not None:
            self._start(lambda: self._ai.prepare_again(insight))

    def _start(self, prepare: Callable[[], PreparedRequest]) -> None:
        if self.busy:
            return
        try:
            prepared = prepare()
        except AIDisabledError:
            self._show_status(tr("AI is off. Choose a local or online provider above; the summary "
                              "works without AI."), error=True)
            return
        except MoneyManagerError as exc:
            self._show_status(str(exc), error=True)
            return
        consent = None
        if prepared.disclosure.requires_consent:
            consent = consent_dialog.ask_consent(self, prepared.disclosure)
            if consent is None:
                self._show_status(tr("Cancelled. Nothing was sent."))
                return
        where = (tr("on this computer") if not prepared.provider.is_online
                 else f"at {prepared.provider.destination}")
        self._show_status(tr("Asking {0} ({1}) {2}…", prepared.provider.name, prepared.provider.model, where))
        self._call = run_in_background(lambda: self._ai.send(prepared, consent),
                                       partial(self._answered, prepared), self._failed,
                                       owner=self)
        self._update_actions()

    def _answered(self, prepared: PreparedRequest, response: AIResponse) -> None:
        try:
            insight = self._ai.record(prepared, response)
        except MoneyManagerError as exc:
            self._show_status(tr("The answer could not be saved: {0}", exc), error=True)
            self._update_actions()
            return
        if prepared.kind is InsightKind.QUESTION:
            self.question_edit.clear()
        self._show_status("")
        self.show_insight(insight)
        self.reload_history()

    def _failed(self, exc: BaseException) -> None:
        if isinstance(exc, MoneyManagerError):
            message = str(exc)
        else:
            logger.error("AI request failed unexpectedly (%s)", type(exc).__name__)
            message = tr("The AI request failed unexpectedly.")
        self._show_status(tr("{0} The rest of Money Manager keeps working normally.", message),
                          error=True)
        self._update_actions()

    # --------------------------------------------------------------- answers

    def show_insight(self, insight: Insight) -> None:
        self.current = insight
        self.answer_title.setText(insight.title)
        where = tr("sent to Anthropic") if insight.is_online else tr("processed on this computer")
        created = local_time(insight.created_at)
        truncated = tr(" · The answer was cut off at the length limit.") if insight.truncated else ""
        self.answer_meta.setText(
            f"{tr(KIND_LABELS[insight.kind])} · {period_text(insight.period)} · {insight.provider} "
            f"{insight.model} ({where}) · {format_date(created.date())} "
            f"{created:%H:%M}{truncated}")
        self.answer_view.setMarkdown(insight.answer)
        unchecked = unsupported_numbers(insight.answer, insight.context)
        self.number_warning.setText(
            tr("Not found in your data, so possibly wrong: ") + ", ".join(unchecked)
            if unchecked else "")
        self.number_warning.setVisible(bool(unchecked))
        self.answer_box.show()
        self._update_actions()

    def show_context(self) -> None:
        if self.current is None:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("What the AI received"))
        dialog.setMinimumSize(640, 520)
        note = QLabel(tr("This analysis and task were given to the AI ")
                      + (tr("(sent to Anthropic).") if self.current.is_online
                         else tr("(processed on this computer).")))
        note.setWordWrap(True)
        text = QPlainTextEdit(self.current.context)
        text.setReadOnly(True)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject)
        layout = QVBoxLayout(dialog)
        layout.addWidget(note)
        layout.addWidget(text, 1)
        layout.addWidget(buttons)
        dialog.exec()

    def _history_selected(self, item: QListWidgetItem | None, _previous: object) -> None:
        if item is None:
            return
        try:
            insight = self._ai.insight(int(item.data(Qt.ItemDataRole.UserRole)))
        except MoneyManagerError as exc:
            self._show_status(str(exc), error=True)
            self.reload_history()
            return
        self.show_insight(insight)

    def delete_selected(self) -> None:
        item = self.history_list.currentItem()
        if item is None:
            return
        insight_id = int(item.data(Qt.ItemDataRole.UserRole))
        try:
            self._ai.delete_insight(insight_id)
        except MoneyManagerError as exc:
            self._show_status(str(exc), error=True)
        if self.current is not None and self.current.id == insight_id:
            self.current = None
            self.answer_box.hide()
        self.reload_history()

    def clear_history(self) -> None:
        if self.history_list.count() == 0:
            return
        if not dialogs.confirm_destructive(
                self, tr("Clear insight history"),
                tr("Delete every stored AI answer? Your financial data is not affected."),
                tr("Clear history")):
            return
        self._ai.clear_history()
        self.current = None
        self.answer_box.hide()
        self.reload_history()

    # -------------------------------------------------------------- provider

    def _load_provider(self) -> None:
        settings = self._ai.settings()
        self.provider_combo.blockSignals(True)
        self.provider_combo.setCurrentIndex(self.provider_combo.findData(settings.mode.value))
        self.provider_combo.blockSignals(False)
        self._show_mode(settings)

    def _provider_chosen(self) -> None:
        mode = AIMode(self.provider_combo.currentData())
        try:
            settings = self._ai.set_mode(mode)
        except MoneyManagerError as exc:
            self._load_provider()  # back to the saved choice
            self._show_status(tr("{0} Open AI settings to set it up.", exc), error=True)
            return
        self._show_status("")
        self._show_mode(settings)

    def _show_mode(self, settings: AISettings) -> None:
        text, online = mode_notice(settings, self._ai.key_status().available)
        self.mode_notice.setText(text)
        self.mode_notice.setObjectName("PrivacyNotice" if online else "MutedLabel")
        self.mode_notice.style().unpolish(self.mode_notice)
        self.mode_notice.style().polish(self.mode_notice)
        self._update_actions()

    # --------------------------------------------------------------- helpers

    def create_account(self) -> None:
        dialog = AccountDialog(self._services, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _update_actions(self) -> None:
        mode = AIMode(self.provider_combo.currentData())
        has_data = self.analysis is not None and self.analysis.has_accounts
        can_ask = mode is not AIMode.OFF and has_data and not self.busy
        for button in (*self.task_buttons.values(), self.ask_button):
            button.setEnabled(can_ask)
        self.question_edit.setEnabled(mode is not AIMode.OFF and has_data)
        self.regenerate_button.setEnabled(can_ask and self.current is not None)
        self.provider_combo.setEnabled(not self.busy)
        self.delete_button.setEnabled(self.history_list.currentItem() is not None)
        self.clear_button.setEnabled(self.history_list.count() > 0)

    def _show_status(self, message: str, *, error: bool = False) -> None:
        self.status_label.setText(message)
        self.status_label.setObjectName("FieldError" if error else "MutedLabel")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
        self.status_label.setVisible(bool(message))


def _pair(label: QLabel, field: QWidget) -> QWidget:
    """A label and its field that stay together when the row wraps."""
    box = QWidget()
    layout = QHBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(Spacing.SM)
    layout.addWidget(label)
    layout.addWidget(field)
    return box

