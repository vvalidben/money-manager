"""Importing a bank statement into an account."""

from datetime import timedelta
from pathlib import Path

import pytest

from money_manager.core.errors import ValidationError
from money_manager.domain.entities import Account, Category, TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.money import Money
from money_manager.domain.statement import guess_columns
from money_manager.services import AppServices
from tests.services.support import fixed_today

TODAY = fixed_today()
D = TODAY.strftime("%d/%m/%Y")
YESTERDAY = (TODAY - timedelta(days=1)).strftime("%d/%m/%Y")


@pytest.fixture
def bank(app_services: AppServices) -> Account:
    return app_services.accounts.create("Bank", opening_balance="1000",
                                        opening_date=TODAY - timedelta(days=30))


@pytest.fixture
def cats(app_services: AppServices) -> tuple[Category, Category]:
    return (app_services.categories.create("Imported spending", CategoryKind.EXPENSE),
            app_services.categories.create("Imported income", CategoryKind.INCOME))


def write(tmp_path: Path, text: str, encoding: str = "utf-8") -> Path:
    path = tmp_path / "statement.csv"
    path.write_bytes(text.encode(encoding))
    return path


def test_preview_then_import(app_services: AppServices, bank: Account,
                             cats: tuple[Category, Category], tmp_path: Path) -> None:
    path = write(tmp_path, f"Date;Libellé;Montant\n{YESTERDAY};CB MARJANE;-642,30\n"
                           f"{D};VIREMENT SALAIRE;14 500,00\n")
    service = app_services.statements
    table = service.read(path)
    columns = guess_columns(table.header)
    preview = service.preview(table, bank.id, columns, "%d/%m/%Y")
    assert len(preview.new_lines) == 2 and preview.duplicate_count == 0

    outcome = service.import_lines(bank.id, preview.new_lines, expense_category_id=cats[0].id,
                                   income_category_id=cats[1].id, source="statement.csv")

    assert (outcome.imported, outcome.duplicates, outcome.problems) == (2, 0, ())
    assert app_services.balances.balance(bank.id) == Money.of("14857.70")
    kinds = sorted((t.type, t.category_id, t.notes) for t in app_services.transactions.list())
    assert kinds == [(TransactionType.EXPENSE, cats[0].id, "Imported from statement.csv"),
                     (TransactionType.INCOME, cats[1].id, "Imported from statement.csv")]


def test_importing_twice_adds_nothing(app_services: AppServices, bank: Account,
                                      cats: tuple[Category, Category], tmp_path: Path) -> None:
    path = write(tmp_path, f"Date;Libellé;Montant\n{D};Coffee;-3,50\n{D};Coffee;-3,50\n")
    service = app_services.statements
    table = service.read(path)
    columns = guess_columns(table.header)
    lines = service.preview(table, bank.id, columns, "%d/%m/%Y").new_lines
    service.import_lines(bank.id, lines, expense_category_id=cats[0].id,
                         income_category_id=cats[1].id)
    again = service.preview(table, bank.id, columns, "%d/%m/%Y")
    assert again.new_lines == [] and again.duplicate_count == 2  # both coffees are known
    outcome = service.import_lines(bank.id, [p.line for p in again.lines],
                                   expense_category_id=cats[0].id, income_category_id=cats[1].id)
    assert (outcome.imported, outcome.duplicates) == (0, 2)
    assert len(app_services.transactions.list()) == 2


def test_partial_duplicates_are_counted(app_services: AppServices, bank: Account,
                                        cats: tuple[Category, Category], tmp_path: Path) -> None:
    app_services.transactions.create(TransactionDraft(
        bank.id, TransactionType.EXPENSE, "3.50", TODAY, cats[0].id, description="coffee"))
    table = app_services.statements.read(
        write(tmp_path, f"Date;Libellé;Montant\n{D};Coffee;-3,50\n{D};Coffee;-3,50\n"))
    preview = app_services.statements.preview(table, bank.id, guess_columns(table.header),
                                              "%d/%m/%Y")
    assert [p.duplicate for p in preview.lines] == [True, False]


def test_lines_that_cannot_be_recorded_are_reported(app_services: AppServices, bank: Account,
                                                    cats: tuple[Category, Category],
                                                    tmp_path: Path) -> None:
    too_early = (TODAY - timedelta(days=90)).strftime("%d/%m/%Y")
    table = app_services.statements.read(write(
        tmp_path, f"Date;Libellé;Montant\n{too_early};Old;-10\n{D};New;-20\n"))
    lines = app_services.statements.preview(table, bank.id, guess_columns(table.header),
                                            "%d/%m/%Y").new_lines
    outcome = app_services.statements.import_lines(
        bank.id, lines, expense_category_id=cats[0].id, income_category_id=cats[1].id)
    assert outcome.imported == 1
    [problem] = outcome.problems
    assert problem.row == 2
    assert app_services.balances.balance(bank.id) == Money.of("980")


def test_windows_encoded_files_are_read(app_services: AppServices, tmp_path: Path) -> None:
    table = app_services.statements.read(
        write(tmp_path, f"Date;Libellé;Montant\n{D};Café;-3,50\n", encoding="cp1252"))
    assert table.header[1] == "Libellé" and table.rows[0][1] == "Café"


def test_empty_files_are_refused(app_services: AppServices, tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="no lines"):
        app_services.statements.read(write(tmp_path, "Date;Libellé;Montant\n"))
