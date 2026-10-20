"""The French interface: every text has a translation, placeholders match, and the
app works in French (numbers, dates and every page)."""

import ast
import string
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from money_manager.core import i18n
from money_manager.core.i18n import resolve_language, set_language, tr
from money_manager.core.locales.ar import CATALOG as ARABIC
from money_manager.core.locales.fr import CATALOG

CATALOGS = {"fr": CATALOG, "ar": ARABIC}
from money_manager.domain.money import Money

SRC = Path(__file__).resolve().parents[1] / "src" / "money_manager"
# The same in both languages, or never shown to people.
UNTRANSLATED = {"Python", "SQLite", "Qt / PySide6", "Euro", "Question", "Suggestions",
                "Animations", "Version", "Budgets", "Type", "Date", "Description", "Notes",
                "Note", "Local", "Net", "Crypto", "Active", "Version {0}",
                "Money Manager {0:%Y}.pdf", "Money Manager {0:%Y-%m}.pdf",
                "Unknown page: {0!r}", "Duplicate navigation key: {0!r}",
                "Unknown fill colour: {0!r}", "Unsupported value type {0}"}


def source_texts() -> set[str]:
    texts = set()
    for path in SRC.rglob("*.py"):
        if "locales" in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "tr" and node.args
                    and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)):
                texts.add(node.args[0].value)
    return texts


def fields(template: str) -> list[str]:
    return sorted(f"{name}!{conversion}:{spec}" for _, name, spec, conversion
                  in string.Formatter().parse(template) if name is not None)


@pytest.fixture
def french() -> Iterator[None]:
    set_language("fr")
    yield
    set_language("en")


@pytest.mark.parametrize("code", sorted(CATALOGS))
def test_every_text_has_a_translation(code: str) -> None:
    missing = sorted(t for t in source_texts() - UNTRANSLATED if t not in CATALOGS[code])
    assert missing == []


@pytest.mark.parametrize("code", sorted(CATALOGS))
def test_translations_keep_their_placeholders(code: str) -> None:
    wrong = [english for english, text in CATALOGS[code].items()
             if fields(english.split("|", 1)[-1]) != fields(text)]
    assert wrong == []


def test_both_languages_translate_the_same_texts() -> None:
    assert set(CATALOG) == set(ARABIC)


def test_english_is_the_default_and_unchanged() -> None:
    assert i18n.language() == "en"
    assert tr("Settings") == "Settings"
    assert tr("{0} per month", "5") == "5 per month"


def test_french_texts_and_formats(french: None) -> None:
    from money_manager.ui.formatting import (
        format_compact_amount,
        format_date,
        format_money,
        format_percent,
        type_label,
    )
    from money_manager.domain.enums import TransactionType

    assert tr("Settings") == "Paramètres"
    assert tr("{0} per month", "5") == "5 par mois"
    assert tr("Not in the catalogue") == "Not in the catalogue"
    assert format_money(Money.of("-12000.5")) == "−12 000,50 MAD"
    assert format_percent(Decimal("0.3817")) == "38,2 %"
    assert format_date(date(2026, 3, 5)) == "05 mars 2026"
    assert format_compact_amount(Decimal("1500")) == "1,5k"
    assert type_label(TransactionType.EXPENSE) == "Dépense"
    assert str(Money.of("1234.5")) == "1 234,50 MAD"


def test_language_setting(app_services) -> None:  # noqa: ANN001
    settings = app_services.settings
    assert settings.language() == "system"
    assert settings.set_language("fr") == "fr" and settings.language() == "fr"
    with pytest.raises(Exception, match="languages"):
        settings.set_language("de")
    assert resolve_language("fr") == "fr" and resolve_language("xx") == "en"
    assert resolve_language("system") in ("en", "fr")


def test_every_page_opens_in_french(french: None, qapp: QApplication, app_config,  # noqa: ANN001
                                    app_services) -> None:  # noqa: ANN001
    from money_manager.domain.entities import TransactionDraft
    from money_manager.domain.enums import CategoryKind, TransactionType
    from money_manager.ui.main_window import MainWindow
    from money_manager.ui.pages import PAGES

    bank = app_services.accounts.create("Banque", opening_balance="1000",
                                        opening_date=date(2026, 1, 1))
    food = app_services.categories.create("Courses", CategoryKind.EXPENSE)
    app_services.transactions.create(TransactionDraft(bank.id, TransactionType.EXPENSE, "45",
                                                      date(2026, 6, 3), food.id))
    app_services.debts.create("Sami", direction="lent", amount="100",
                              start_date=date(2026, 6, 1))
    window = MainWindow(app_config, app_services)
    window.show()
    try:
        for spec in PAGES:
            window.show_page(spec.key)
            QApplication.processEvents()
        assert window.page("transactions").add_button.text() == "Ajouter une opération"
    finally:
        window.close()



@pytest.fixture
def arabic() -> Iterator[None]:
    set_language("ar")
    yield
    set_language("en")


def test_arabic_texts_and_formats(arabic: None) -> None:
    from money_manager.core.i18n import is_right_to_left
    from money_manager.ui.formatting import format_date, format_money, format_percent

    assert is_right_to_left()
    assert tr("Settings") == "الإعدادات"
    # Western digits, kept left to right inside Arabic text.
    assert format_money(Money.of("-12000.5")) == "\u200e−12\u00a0000,50\u00a0MAD\u200e"
    assert format_percent(Decimal("0.382")) == "38,2\u00a0%"
    assert format_date(date(2026, 8, 5)) == "05 غشت 2026"  # Moroccan month names


def test_every_page_opens_in_arabic(arabic: None, qapp: QApplication, app_config,  # noqa: ANN001
                                    app_services) -> None:  # noqa: ANN001
    from PySide6.QtCore import Qt

    from money_manager.ui.main_window import MainWindow
    from money_manager.ui.pages import PAGES

    app_services.accounts.create("Bank", opening_balance="100", opening_date=date(2026, 1, 1))
    qapp.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    window = MainWindow(app_config, app_services)
    window.resize(1200, 800)
    window.show()
    try:
        for spec in PAGES:
            window.show_page(spec.key)
            QApplication.processEvents()
        assert window.page("transactions").add_button.text() == "إضافة عملية"
        rail = window.sidebar
        assert rail.geometry().right() == window.centralWidget().width() - 1  # right edge
    finally:
        window.close()
        qapp.setLayoutDirection(Qt.LayoutDirection.LeftToRight)


def test_reports_in_arabic(arabic: None, qapp: QApplication, app_services,  # noqa: ANN001
                           tmp_path: Path) -> None:
    from money_manager.ui.reports.monthly_pdf import report_html, write_monthly_report
    from money_manager.ui.reports.yearly_pdf import write_yearly_report

    app_services.accounts.create("Bank", opening_balance="100", opening_date=date(2026, 1, 1))
    report = app_services.reports.monthly(date(2026, 5, 1))
    assert "dir='rtl'" in report_html(report) and "الملخص" in report_html(report)
    write_monthly_report(report, tmp_path / "month.pdf")
    write_yearly_report(app_services.reports.yearly(2026), tmp_path / "year.pdf")
    assert (tmp_path / "month.pdf").read_bytes().startswith(b"%PDF")
    assert (tmp_path / "year.pdf").read_bytes().startswith(b"%PDF")
