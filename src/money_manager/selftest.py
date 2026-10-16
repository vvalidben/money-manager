"""Built-in self-test for verifying a packaged build.

    MoneyManager.exe --self-test C:\\path\\to\\empty-folder

Runs the real application code (bundled assets, database migrations, SQLite,
services and every page) against ``<folder>\\data`` — never the user's real
data or configuration, and never the Windows Credential Manager — then writes
``report.json`` and a screenshot of each page to the folder and exits with 0
when every check passed. Running it a second time on the same folder checks
that the first run's data persisted.
"""

import json
import logging
import sys
import time
import traceback
from collections.abc import Callable, Sequence
from datetime import timedelta
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QApplication

from money_manager import APP_NAME, __version__
from money_manager.ai.secrets import MemorySecretStore
from money_manager.ai.settings import AIMode, AISettings
from money_manager.core.config import AppConfig
from money_manager.core.resources import is_frozen, resource_path
from money_manager.domain.entities import TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.money import Money
from money_manager.domain.periods import StatsRange
from money_manager.persistence.database import Database
from money_manager.persistence.migrator import current_revision, head_revision
from money_manager.services import AppServices
from money_manager.ui.main_window import MainWindow
from money_manager.ui.pages import PAGES

logger = logging.getLogger(__name__)

SELF_TEST_FLAG = "--self-test"
EXPECTED_BALANCE = Money.of("4700")  # 1,000 opening + 5,000 income − 1,200 − 100 expenses


def self_test_folder(argv: Sequence[str]) -> Path | None:
    """The folder given after ``--self-test``, if the flag is present."""
    arguments = list(argv)
    if SELF_TEST_FLAG not in arguments:
        return None
    index = arguments.index(SELF_TEST_FLAG)
    if index + 1 >= len(arguments):
        raise SystemExit(f"{SELF_TEST_FLAG} needs a folder")
    return Path(arguments[index + 1]).resolve()


class SelfTest:
    def __init__(self, folder: Path, app: QApplication) -> None:
        self.folder = folder
        self.app = app
        self.checks: list[dict[str, Any]] = []

    def check(self, name: str, action: Callable[[], object]) -> object:
        started = time.perf_counter()
        try:
            detail = action()
            ok = detail is not False
        except Exception as exc:  # noqa: BLE001 - every failure goes into the report
            ok, detail = False, f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        self.checks.append({"name": name, "ok": ok, "seconds": round(time.perf_counter() - started, 3),
                            "detail": detail if isinstance(detail, str) else None})
        return detail

    def settle(self, seconds: float = 0.3) -> None:
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.app.processEvents()
            time.sleep(0.01)

    # ------------------------------------------------------------ scenario

    def run(self) -> int:
        from money_manager.app import initialize_backend  # the real start-up path

        self.folder.mkdir(parents=True, exist_ok=True)
        config = AppConfig(data_dir=self.folder / "data")
        database: Database | None = None
        phase = "?"
        try:
            database = self.check("database initialises", lambda: initialize_backend(config))
            assert isinstance(database, Database), "the database could not be opened"
            services = AppServices.create(database, secret_store=MemorySecretStore(), environ={})
            self.check("bundled resources are found", self.check_resources)
            self.check("schema is current",
                       lambda: current_revision(database.engine) == head_revision())
            phase = "restart" if services.accounts.list() else "first run"
            if phase == "first run":
                self.first_run(services)
            else:
                self.second_run(services)
            self.check("dashboard total", lambda: services.dashboard.overview().total_balance
                       == services.balances.total_balance())
            self.check("statistics", lambda: services.statistics.report(
                services.statistics.range_for(StatsRange.MONTHS_3)).totals.income.is_positive())
            self.check("pages open and render", lambda: self.visit_pages(config, services))
        finally:
            if database is not None:
                database.dispose()
        passed = all(c["ok"] for c in self.checks)
        report = {"application": APP_NAME, "version": __version__, "frozen": is_frozen(),
                  "executable": sys.executable, "data_dir": str(config.data_dir),
                  "phase": phase, "passed": passed, "checks": self.checks}
        (self.folder / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return 0 if passed else 1

    def check_resources(self) -> str:
        required = [resource_path("ui", "assets", "chevron-down.svg"),
                    resource_path("ui", "assets", "app_icon.png"),
                    resource_path("persistence", "migrations", "env.py"),
                    resource_path("persistence", "migrations", "script.py.mako")]
        missing = [str(p) for p in required if not p.is_file()]
        versions = list(resource_path("persistence", "migrations", "versions").glob("0*.py"))
        assert not missing, f"missing: {missing}"
        assert len(versions) >= 8, f"only {len(versions)} migrations bundled"
        return f"{len(versions)} migrations, assets at {resource_path('ui', 'assets')}"

    def first_run(self, s: AppServices) -> None:
        today = s.today()
        state: dict[str, Any] = {}

        def accounts() -> None:
            state["bank"] = s.accounts.create("Self-test bank", opening_balance="1000",
                                              opening_date=today - timedelta(days=40))
            state["salary"] = s.categories.create("Salary", CategoryKind.INCOME)
            state["food"] = s.categories.create("Food", CategoryKind.EXPENSE)

        def transactions() -> None:
            bank, food = state["bank"].id, state["food"].id
            s.transactions.create(TransactionDraft(bank, TransactionType.INCOME, "5000",
                                                   today - timedelta(days=5),
                                                   state["salary"].id, "Salary"))
            s.transactions.create(TransactionDraft(bank, TransactionType.EXPENSE, "1200", today,
                                                   food, "Groceries"))

        def allocations() -> bool:
            pot = s.allocations.create("Holiday", initial_amount="300")
            s.transfers.transfer(from_allocation_id=None, to_allocation_id=pot.id, amount="200")
            s.transactions.create(TransactionDraft(state["bank"].id, TransactionType.EXPENSE,
                                                   "100", today, state["food"].id, "Tickets",
                                                   allocation_id=pot.id))
            return s.allocations.balance(pot.id) == Money.of("400")

        self.check("create accounts and categories", accounts)
        self.check("record transactions", transactions)
        self.check("allocations and transfers", allocations)
        self.check("balance", lambda: s.balances.total_balance() == EXPECTED_BALANCE)
        self.check("goals, subscriptions, investments", lambda: self.other_features(s, state))
        self.check("AI configuration", lambda: self.configure_ai(s))
        self.check("settings and backup", lambda: self.settings(s))

    @staticmethod
    def other_features(s: AppServices, state: dict[str, Any]) -> bool:
        today = s.today()
        s.goals.create_manual("Laptop", target="8000", current="500")
        s.subscriptions.create("Streaming", amount="65", frequency="monthly",
                               next_payment_date=today + timedelta(days=3),
                               category_id=state["food"].id, account_id=state["bank"].id)
        fund = s.investments.create("Index fund", "etf")
        s.investments.add_contribution(fund.investment.id, "250", today)
        s.investments.set_value(fund.investment.id, "260", today)
        return s.investments.summary().total_value == Money.of("260")

    @staticmethod
    def configure_ai(s: AppServices) -> str:
        s.ai.save_settings(AISettings(AIMode.LOCAL, local_model="llama3.2"))
        s.ai.save_api_key("sk-ant-self-test-not-a-real-key-0000")  # memory only
        status = s.ai.check_availability()  # no network probe
        return f"local model configured; availability: {status.message}"

    def settings(self, s: AppServices) -> str:
        info = s.settings.application_info()
        summary = s.data.export_backup(self.folder / "backup.json")
        s.data.export_transactions_csv(self.folder / "transactions.csv")
        return f"{info.name} {info.version}, schema {info.schema_revision}, " \
               f"backup of {summary.total_rows} records"

    def second_run(self, s: AppServices) -> None:
        self.check("data persisted", lambda: [a.name for a in s.accounts.list()]
                   == ["Self-test bank"] and len(s.transactions.list()) == 3)
        self.check("balance persisted", lambda: s.balances.total_balance() == EXPECTED_BALANCE)
        self.check("allocation persisted", lambda: [(a.name, s.allocations.balance(a.id))
                   for a in s.allocations.list()] == [("Holiday", Money.of("400"))])
        self.check("AI settings persisted", lambda: s.ai.settings().mode is AIMode.LOCAL)
        self.check("goals, subscriptions, investments persisted",
                   lambda: (len(s.goals.list()), len(s.subscriptions.list()),
                            len(s.investments.list())) == (1, 1, 1))

    def visit_pages(self, config: AppConfig, services: AppServices) -> str:
        window = MainWindow(config, services)
        window.resize(1280, 860)
        window.show()
        screens = self.folder / "screens"
        screens.mkdir(exist_ok=True)
        try:
            for spec in PAGES:
                window.show_page(spec.key)
                page = window.current_page
                deadline = time.monotonic() + 10
                while getattr(page, "loading", False) and time.monotonic() < deadline:
                    self.settle(0.05)
                self.settle()
                assert page.header.title_label.text() == spec.title
                # Headless, the pointer rests on the rail and opens it: close it for the picture.
                window.sidebar.set_expanded(False)
                window.sidebar.place(window.centralWidget().height())
                window.grab().save(str(screens / f"{spec.key}.png"))
        finally:
            window.close()
            window.deleteLater()
            self.settle(0.1)
        return f"{len(PAGES)} pages"


def run_self_test(folder: Path, app: QApplication) -> int:
    return SelfTest(folder, app).run()
