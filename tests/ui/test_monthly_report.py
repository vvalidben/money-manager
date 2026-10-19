"""The monthly report: gathered figures, the PDF, and saving it from Statistics."""

from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from money_manager.core.errors import ValidationError
from money_manager.domain.entities import Account, Category, TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.money import Money
from money_manager.domain.periods import DateRange
from money_manager.services import AppServices
from money_manager.ui import dialogs
from money_manager.ui.pages import PAGES, STATISTICS_PAGE_KEY
from money_manager.ui.reports.monthly_pdf import (
    NET_WORTH_URL,
    SPENDING_URL,
    report_html,
    write_monthly_report,
)
from money_manager.ui.statistics.statistics_page import StatisticsPage, default_report_path

SPEC = next(spec for spec in PAGES if spec.key == STATISTICS_PAGE_KEY)  # today: 15 Jun 2026


@pytest.fixture
def data(app_services: AppServices) -> dict[str, Category]:
    bank: Account = app_services.accounts.create("Bank", opening_balance="1000",
                                                 opening_date=date(2026, 4, 1))
    cats = {"salary": app_services.categories.create("Salary", CategoryKind.INCOME),
            "food": app_services.categories.create("Food & <drinks>", CategoryKind.EXPENSE),
            "rent": app_services.categories.create("Rent", CategoryKind.EXPENSE)}
    for type_, amount, cat, on, text in (
        (TransactionType.INCOME, "5000", "salary", date(2026, 4, 1), "April pay"),
        (TransactionType.EXPENSE, "400", "food", date(2026, 4, 9), "Market"),
        (TransactionType.INCOME, "5200", "salary", date(2026, 5, 1), "May pay"),
        (TransactionType.EXPENSE, "1500", "rent", date(2026, 5, 3), "Rent <May>"),
        (TransactionType.EXPENSE, "650", "food", date(2026, 5, 20), "Market"),
        (TransactionType.EXPENSE, "90", "food", date(2026, 6, 2), "Bakery"),
    ):
        app_services.transactions.create(TransactionDraft(bank.id, type_, amount, on,
                                                          cats[cat].id, description=text))
    app_services.budgets.set(cats["food"].id, "600")
    return cats


class TestService:
    def test_months_newest_first(self, app_services: AppServices, data: object) -> None:
        assert app_services.reports.months() == [date(2026, 6, 1), date(2026, 5, 1),
                                                 date(2026, 4, 1)]

    def test_a_whole_month_against_the_month_before(self, app_services: AppServices,
                                                    data: dict[str, Category]) -> None:
        report = app_services.reports.monthly(date(2026, 5, 17))
        assert report.month == date(2026, 5, 1) and report.is_complete
        assert report.statistics.previous_period == DateRange(date(2026, 4, 1), date(2026, 4, 30))
        assert report.statistics.totals.income == Money.of("5200")
        assert report.statistics.previous_totals.income == Money.of("5000")
        [food] = report.budgets.statuses
        assert food.spent == Money.of("650") and food.level.value == "over"
        assert [t.description for t in report.largest_expenses] == ["Rent <May>", "Market"]
        assert report.balance == Money.of("8650")  # 1000 + 5000 − 400 + 5200 − 1500 − 650

    def test_the_current_month_to_date(self, app_services: AppServices, data: object) -> None:
        report = app_services.reports.monthly(date(2026, 6, 1))
        assert not report.is_complete
        assert report.period == DateRange(date(2026, 6, 1), date(2026, 6, 15))
        assert report.statistics.previous_period == DateRange(date(2026, 5, 1), date(2026, 5, 15))
        assert report.budgets.statuses[0].spent == Money.of("90")

    def test_months_outside_tracking_are_refused(self, app_services: AppServices,
                                                 data: object) -> None:
        with pytest.raises(ValidationError):
            app_services.reports.monthly(date(2026, 3, 1))
        with pytest.raises(ValidationError):
            app_services.reports.monthly(date(2026, 7, 1))


class TestPdf:
    def test_html_has_every_section_and_escapes_text(self, app_services: AppServices,
                                                     data: object) -> None:
        html = report_html(app_services.reports.monthly(date(2026, 5, 1)),
                           charts={NET_WORTH_URL, SPENDING_URL})
        for text in ("May 2026", "1–31 May", "5,200.00 MAD", "vs Apr 2026", "Net worth",
                     "Budgets", "Over", "Largest expenses", "Food &amp; &lt;drinks&gt;",
                     "Rent &lt;May&gt;", NET_WORTH_URL, SPENDING_URL):
            assert text in html
        assert "<May>" not in html and "<drinks>" not in html

    def test_writes_a_pdf(self, qapp: QApplication, app_services: AppServices, data: object,
                          tmp_path: Path) -> None:
        path = tmp_path / "may.pdf"
        write_monthly_report(app_services.reports.monthly(date(2026, 5, 1)), path)
        assert path.read_bytes().startswith(b"%PDF") and path.stat().st_size > 10_000


@pytest.fixture
def page(qapp: QApplication, app_services: AppServices) -> Iterator[StatisticsPage]:
    widget = StatisticsPage(SPEC, app_services)
    widget.resize(1200, 800)
    widget.show()
    yield widget
    widget.close()
    widget.deleteLater()


class TestPage:
    def test_save_and_open(self, page: StatisticsPage, data: object, tmp_path: Path,
                           monkeypatch: pytest.MonkeyPatch) -> None:
        asked: list[list[date]] = []
        monkeypatch.setattr(page, "ask_report_month",
                            lambda months: asked.append(months) or months[1])
        monkeypatch.setattr(page, "ask_report_path", lambda suggested: tmp_path / suggested.name)
        opened: list[Path] = []
        monkeypatch.setattr(page, "open_report", opened.append)
        notices: list[tuple[str, str]] = []
        page.notice.connect(lambda title, detail: notices.append((title, detail)))

        page.report_button.click()

        target = tmp_path / "Money Manager 2026-05.pdf"
        assert target.read_bytes().startswith(b"%PDF")
        assert opened == [target]
        assert notices == [("Report saved", target.name)]

    def test_cancelling_writes_nothing(self, page: StatisticsPage, data: object,
                                       monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(page, "ask_report_month", lambda months: months[0])
        monkeypatch.setattr(page, "ask_report_path", lambda suggested: None)
        assert page.save_report() is None

    def test_without_accounts(self, page: StatisticsPage,
                              monkeypatch: pytest.MonkeyPatch) -> None:
        shown: list[str] = []
        monkeypatch.setattr(dialogs, "show_info", lambda _p, title, _m: shown.append(title))
        assert page.save_report() is None
        assert shown == ["Monthly report"]

    def test_default_file_name(self) -> None:
        assert default_report_path(date(2026, 9, 1)).name == "Money Manager 2026-09.pdf"
