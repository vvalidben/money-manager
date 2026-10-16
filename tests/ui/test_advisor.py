"""AI Advisor page: summary without AI, the request flow, failures and history."""

import threading
import time
from collections.abc import Callable, Iterator
from datetime import date

import pytest
from PySide6.QtWidgets import QApplication

from money_manager.ai.settings import AIMode, AISettings
from money_manager.core.errors import AIUnavailableError
from money_manager.domain.entities import Account, Category, TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.insights import InsightKind
from money_manager.services import AppServices
from money_manager.ui import dialogs
from money_manager.ui.advisor.advisor_page import AdvisorPage
from money_manager.ui.ai import consent_dialog
from money_manager.ui.ai.background import run_in_background
from money_manager.ui.main_window import MainWindow
from money_manager.ui.pages import AI_ADVISOR_PAGE_KEY, PAGES, SETTINGS_PAGE_KEY
from tests.ai.support import ScriptedProvider

SPEC = next(spec for spec in PAGES if spec.key == AI_ADVISOR_PAGE_KEY)
LOCAL = AISettings(AIMode.LOCAL, local_model="llama3.2")
ONLINE = AISettings(AIMode.ONLINE)


def wait_until(condition: Callable[[], bool], timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while not condition():
        if time.monotonic() > deadline:
            raise AssertionError("timed out waiting for the background request")
        QApplication.processEvents()
        time.sleep(0.005)


@pytest.fixture
def household(app_services: AppServices) -> Account:
    bank = app_services.accounts.create("Bank", opening_balance="5000",
                                        opening_date=date(2026, 1, 1))
    salary = app_services.categories.create("Salary", CategoryKind.INCOME)
    food = app_services.categories.create("Food", CategoryKind.EXPENSE)

    def add(type_: TransactionType, amount: str, category: Category, on: date) -> None:
        app_services.transactions.create(TransactionDraft(bank.id, type_, amount, on,
                                                          category.id, description="private"))

    for month in (5, 6):
        add(TransactionType.INCOME, "12000", salary, date(2026, month, 1))
    add(TransactionType.EXPENSE, "1700", food, date(2026, 5, 4))
    add(TransactionType.EXPENSE, "2100", food, date(2026, 6, 4))
    return bank


@pytest.fixture
def provider(app_services: AppServices, monkeypatch: pytest.MonkeyPatch) -> ScriptedProvider:
    fake = ScriptedProvider()
    monkeypatch.setattr(app_services.ai, "provider", lambda settings=None: fake)
    return fake


@pytest.fixture
def no_consent_prompt(monkeypatch: pytest.MonkeyPatch) -> list[object]:
    asked: list[object] = []

    def refuse(parent: object, disclosure: object) -> None:
        asked.append(disclosure)
        raise AssertionError("local requests must not ask for consent")

    monkeypatch.setattr(consent_dialog, "ask_consent", refuse)
    return asked


@pytest.fixture
def page(qapp: QApplication, app_services: AppServices) -> Iterator[AdvisorPage]:
    widget = AdvisorPage(SPEC, app_services)
    widget.resize(1280, 1000)
    widget.show()
    yield widget
    wait_until(lambda: not widget.busy)
    widget.close()
    widget.deleteLater()


def shown(page: AdvisorPage, settings: AISettings, app_services: AppServices) -> AdvisorPage:
    app_services.ai.save_settings(settings)
    page.on_shown()
    return page


def answer_text(page: AdvisorPage) -> str:
    return page.answer_view.toPlainText()


class TestWithoutAI:
    def test_empty_database(self, page: AdvisorPage) -> None:
        page.on_shown()
        assert page.empty_state.isVisible() and not page._grid.isVisible()
        assert not page.ask_button.isEnabled()

    def test_summary_works_with_ai_off(self, page: AdvisorPage, household: Account) -> None:
        page.on_shown()

        assert page.stat_cards["Income"].value == "+12,000.00 MAD"
        assert page.stat_cards["Expenses"].value == "−2,100.00 MAD"
        assert any("Expenses increased by 23.5%" in fact for fact in page.facts_card.facts)
        assert "AI is off" in page.mode_notice.text()
        assert not any(b.isEnabled() for b in page.task_buttons.values())
        assert not page.question_edit.isEnabled()

    def test_period_selection(self, page: AdvisorPage, household: Account) -> None:
        page.on_shown()
        page.period_combo.setCurrentIndex(page.period_combo.findData("last_month"))
        assert page.analysis is not None
        assert (page.analysis.period.start, page.analysis.period.end) == (date(2026, 5, 1),
                                                                          date(2026, 5, 31))
        assert page.stat_cards["Expenses"].value == "−1,700.00 MAD"


class TestAsking:
    def test_local_insight(self, page: AdvisorPage, app_services: AppServices,
                           household: Account, provider: ScriptedProvider,
                           no_consent_prompt: list[object]) -> None:
        shown(page, LOCAL, app_services)
        assert "processed on this computer" in page.mode_notice.text()
        assert page.mode_notice.objectName() == "MutedLabel"

        page.task_buttons[InsightKind.INSIGHTS].click()
        wait_until(lambda: not page.busy)

        [request] = provider.sent
        assert "- Food: 1,700.00 MAD -> 2,100.00 MAD (+23.5%)" in request.user
        assert "private" not in request.user
        assert answer_text(page) == "Food spending rose by 22.0%."
        assert "processed on this computer" in page.answer_meta.text()
        [insight] = app_services.ai.history()
        assert insight.kind is InsightKind.INSIGHTS and page.current == insight
        assert page.history_list.count() == 1

    @pytest.mark.parametrize("kind", [InsightKind.SUGGESTIONS, InsightKind.SPENDING,
                                      InsightKind.MONTHLY])
    def test_every_task(self, page: AdvisorPage, app_services: AppServices, household: Account,
                        provider: ScriptedProvider, kind: InsightKind) -> None:
        shown(page, LOCAL, app_services)
        page.task_buttons[kind].click()
        wait_until(lambda: not page.busy)
        assert app_services.ai.history()[0].kind is kind

    def test_question(self, page: AdvisorPage, app_services: AppServices, household: Account,
                      provider: ScriptedProvider) -> None:
        shown(page, LOCAL, app_services)
        page.ask()
        assert "Type a question" in page.status_label.text() and provider.sent == []

        page.question_edit.setText("Why did food rise?")
        page.ask_button.click()
        wait_until(lambda: not page.busy)

        assert provider.sent[0].user.endswith("Question: Why did food rise?")
        assert page.answer_title.text() == "Why did food rise?"
        assert page.question_edit.text() == ""

    def test_online_requires_confirmation(self, page: AdvisorPage, app_services: AppServices,
                                          household: Account, provider: ScriptedProvider,
                                          monkeypatch: pytest.MonkeyPatch) -> None:
        provider.is_online, provider.name = True, "Anthropic"
        shown(page, ONLINE, app_services)
        assert "api.anthropic.com" in page.mode_notice.text()
        assert page.mode_notice.objectName() == "PrivacyNotice"
        shown_disclosures: list[object] = []

        def cancel(parent: object, disclosure: object) -> None:
            shown_disclosures.append(disclosure)
            return None

        monkeypatch.setattr(consent_dialog, "ask_consent", cancel)
        page.task_buttons[InsightKind.INSIGHTS].click()
        assert provider.sent == [] and "Nothing was sent" in page.status_label.text()
        assert app_services.ai.history() == []

        monkeypatch.setattr(consent_dialog, "ask_consent",
                            lambda parent, disclosure: disclosure.accept())
        page.task_buttons[InsightKind.INSIGHTS].click()
        wait_until(lambda: not page.busy)
        assert len(provider.sent) == 1 and len(shown_disclosures) == 1
        assert "sent to Anthropic" in page.answer_meta.text()

    def test_missing_provider(self, page: AdvisorPage, app_services: AppServices,
                              household: Account) -> None:
        shown(page, AISettings(), app_services)
        page.run_task(InsightKind.INSIGHTS)  # e.g. triggered while AI is off
        assert "AI is off" in page.status_label.text()
        assert page.stat_cards["Income"].value == "+12,000.00 MAD"  # summary unaffected

    def test_provider_failure_keeps_the_app_working(
        self, page: AdvisorPage, app_services: AppServices, household: Account,
        provider: ScriptedProvider,
    ) -> None:
        provider.error = AIUnavailableError("Ollama is not running at http://localhost:11434.")
        shown(page, LOCAL, app_services)

        page.task_buttons[InsightKind.INSIGHTS].click()
        wait_until(lambda: not page.busy)

        assert "Ollama is not running" in page.status_label.text()
        assert "keeps working" in page.status_label.text()
        assert page.status_label.objectName() == "FieldError"
        assert app_services.ai.history() == [] and not page.answer_box.isVisible()
        assert page.task_buttons[InsightKind.INSIGHTS].isEnabled()  # can try again
        assert page.facts_card.facts  # summary still there

    def test_unexpected_failure(self, page: AdvisorPage, app_services: AppServices,
                                household: Account, provider: ScriptedProvider) -> None:
        provider.error = RuntimeError("internal detail")
        shown(page, LOCAL, app_services)
        page.task_buttons[InsightKind.INSIGHTS].click()
        wait_until(lambda: not page.busy)
        assert "failed unexpectedly" in page.status_label.text()
        assert "internal detail" not in page.status_label.text()

    def test_invented_numbers_are_flagged(self, page: AdvisorPage, app_services: AppServices,
                                          household: Account,
                                          provider: ScriptedProvider) -> None:
        provider.reply = "Food rose by about 24%. You spent 2,700 MAD on restaurants."
        shown(page, LOCAL, app_services)
        page.task_buttons[InsightKind.SPENDING].click()
        wait_until(lambda: not page.busy)
        assert page.number_warning.isVisible()
        assert page.number_warning.text().endswith("2,700")  # 24% is in the data (23.5%)

    def test_buttons_are_disabled_while_asking(self, page: AdvisorPage,
                                               app_services: AppServices, household: Account,
                                               provider: ScriptedProvider) -> None:
        shown(page, LOCAL, app_services)
        page.task_buttons[InsightKind.INSIGHTS].click()
        if page.busy:  # the scripted answer may already be back
            assert not page.ask_button.isEnabled() and not page.provider_combo.isEnabled()
        wait_until(lambda: not page.busy)
        assert page.ask_button.isEnabled()


class TestHistory:
    def ask(self, page: AdvisorPage, kind: InsightKind = InsightKind.INSIGHTS) -> None:
        page.task_buttons[kind].click()
        wait_until(lambda: not page.busy)

    def test_regenerate(self, page: AdvisorPage, app_services: AppServices, household: Account,
                        provider: ScriptedProvider) -> None:
        shown(page, LOCAL, app_services)
        self.ask(page, InsightKind.MONTHLY)
        first = page.current
        provider.reply = "A second answer."

        page.regenerate_button.click()
        wait_until(lambda: not page.busy)

        assert page.current is not None and first is not None
        assert page.current.id != first.id and page.current.kind is InsightKind.MONTHLY
        assert page.current.period == first.period
        assert answer_text(page) == "A second answer."
        assert page.history_list.count() == 2

    def test_history_is_stored_and_reopened(self, qapp: QApplication, page: AdvisorPage,
                                            app_services: AppServices, household: Account,
                                            provider: ScriptedProvider) -> None:
        shown(page, LOCAL, app_services)
        self.ask(page)
        provider.reply = "Second."
        self.ask(page, InsightKind.SUGGESTIONS)

        other = AdvisorPage(SPEC, app_services)  # e.g. after restarting the app
        other.on_shown()
        assert other.history_list.count() == 2
        other.history_list.setCurrentRow(1)  # the older one
        assert other.current is not None and other.current.kind is InsightKind.INSIGHTS
        assert other.answer_view.toPlainText() == "Food spending rose by 22.0%."
        other.deleteLater()

    def test_delete_and_clear(self, page: AdvisorPage, app_services: AppServices,
                              household: Account, provider: ScriptedProvider,
                              monkeypatch: pytest.MonkeyPatch) -> None:
        shown(page, LOCAL, app_services)
        self.ask(page)
        self.ask(page)
        page.history_list.setCurrentRow(0)
        page.delete_button.click()
        assert page.history_list.count() == 1 and not page.answer_box.isVisible()

        monkeypatch.setattr(dialogs, "confirm_destructive", lambda *args: False)
        page.clear_button.click()
        assert page.history_list.count() == 1
        monkeypatch.setattr(dialogs, "confirm_destructive", lambda *args: True)
        page.clear_button.click()
        assert page.history_list.count() == 0 and app_services.ai.history() == []
        assert not page.clear_button.isEnabled()


class TestProviderSelection:
    def test_choosing_a_provider_saves_it(self, page: AdvisorPage, app_services: AppServices,
                                          household: Account) -> None:
        page.on_shown()
        page.provider_combo.setCurrentIndex(page.provider_combo.findData("online"))
        assert app_services.ai.settings().mode is AIMode.ONLINE
        assert "Add an Anthropic API key" in page.mode_notice.text()

    def test_local_without_a_model_is_refused(self, page: AdvisorPage,
                                              app_services: AppServices,
                                              household: Account) -> None:
        page.on_shown()
        page.provider_combo.setCurrentIndex(page.provider_combo.findData("local"))
        assert app_services.ai.settings().mode is AIMode.OFF
        assert AIMode(page.provider_combo.currentData()) is AIMode.OFF
        assert "Choose a local model in Settings first" in page.status_label.text()

    def test_settings_button_opens_settings(self, page: AdvisorPage) -> None:
        requested: list[str] = []
        page.navigate_requested.connect(requested.append)
        page.settings_button.click()
        assert requested == [SETTINGS_PAGE_KEY]


def test_main_window_uses_the_advisor_page(qapp: QApplication, app_config: object,
                                           app_services: AppServices) -> None:
    window = MainWindow(app_config, app_services)  # type: ignore[arg-type]
    window.show_page(AI_ADVISOR_PAGE_KEY)
    assert isinstance(window.current_page, AdvisorPage)
    window.current_page.settings_button.click()  # type: ignore[attr-defined]
    assert window.current_page.spec.key == SETTINGS_PAGE_KEY
    window.close()
    window.deleteLater()


def test_background_calls_run_off_the_ui_thread(qapp: QApplication) -> None:
    ui_thread = threading.get_ident()
    seen: dict[str, object] = {}

    def worked(worker_thread: object) -> None:
        seen.update(worker=worker_thread, callback=threading.get_ident())

    def boom() -> None:
        raise ValueError("no")

    ok = run_in_background(threading.get_ident, worked, seen.setdefault)
    wait_until(lambda: "callback" in seen)
    assert seen["worker"] != ui_thread and seen["callback"] == ui_thread and not ok.running

    errors: list[BaseException] = []
    failed = run_in_background(boom, seen.setdefault, errors.append)
    wait_until(lambda: bool(errors))
    assert isinstance(errors[0], ValueError) and not failed.running

