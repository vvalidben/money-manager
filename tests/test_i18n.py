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
from money_manager.core.locales.fr import CATALOG
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


def test_every_text_has_a_french_translation() -> None:
    missing = sorted(t for t in source_texts() - UNTRANSLATED if t not in CATALOG)
    assert missing == []


def test_translations_keep_their_placeholders() -> None:
    wrong = [english for english, french in CATALOG.items() if fields(english) != fields(french)]
    assert wrong == []


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
