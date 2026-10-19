"""Reading bank statements: separators, columns, amounts and dates."""

from datetime import date
from decimal import Decimal

import pytest

from money_manager.domain.statement import (
    StatementColumns,
    detect_date_format,
    guess_columns,
    parse_amount,
    parse_statement,
    read_table,
)


@pytest.mark.parametrize(("text", "value"), [
    ("1 234,56", "1234.56"), ("1,234.56", "1234.56"), ("12.345,67", "12345.67"),
    ("-12,50 DH", "-12.50"), ("(12.50)", "-12.50"), ("45-", "-45"), ("1.500", "1500"),
    ("1,5", "1.5"), ("− 7,10 MAD", "-7.10"), ("+3", "3"), ("1 000,00 €", "1000.00"),
])
def test_amounts(text: str, value: str) -> None:
    assert parse_amount(text) == Decimal(value)


def test_empty_cell_is_no_amount() -> None:
    assert parse_amount("  ") is None


@pytest.mark.parametrize("text", ["abc", "12.3456", "1-2", "--"])
def test_bad_amounts_are_refused_not_guessed(text: str) -> None:
    with pytest.raises(ValueError):
        parse_amount(text)


def test_french_debit_credit_statement() -> None:
    table = read_table("Date opération;Date de valeur;Libellé;Débit;Crédit\n"
                       "03/10/2026;04/10/2026;CB CARREFOUR;412,85;\n"
                       "05/10/2026;05/10/2026;VIREMENT SALAIRE;;14 500,00\n")
    columns = guess_columns(table.header)
    assert columns == StatementColumns(date=0, description=2, debit=3, credit=4)
    fmt = detect_date_format([row[0] for row in table.rows])
    assert fmt == "%d/%m/%Y"
    lines, problems = parse_statement(table, columns, fmt)
    assert problems == []
    assert [(l.row, l.occurred_on, l.description, l.amount) for l in lines] == [
        (2, date(2026, 10, 3), "CB CARREFOUR", Decimal("-412.85")),
        (3, date(2026, 10, 5), "VIREMENT SALAIRE", Decimal("14500.00")),
    ]


def test_english_single_amount_statement() -> None:
    table = read_table('Booking date,Description,Amount\n2026-10-03,Coffee,-3.50\n'
                       '2026-10-04 09:30:00,Salary,"1,200.00"\n')
    columns = guess_columns(table.header)
    assert columns == StatementColumns(date=0, description=1, amount=2)
    fmt = detect_date_format([row[0] for row in table.rows])
    lines, _ = parse_statement(table, columns, fmt)
    assert [l.amount for l in lines] == [Decimal("-3.50"), Decimal("1200.00")]


def test_debits_written_as_negative_numbers_are_still_money_out() -> None:
    table = read_table("Date;Label;Debit;Credit\n01/10/2026;Rent;-4800;\n")
    lines, _ = parse_statement(table, guess_columns(table.header), "%d/%m/%Y")
    assert lines[0].amount == Decimal("-4800")


def test_unreadable_lines_become_problems() -> None:
    table = read_table("Date;Libellé;Montant\n03/10/2026;OK;-10\nnot a date;X;-1\n"
                       "04/10/2026;No amount;\n05/10/2026;Bad;12,345\n06/10/2026\n")
    lines, problems = parse_statement(table, guess_columns(table.header), "%d/%m/%Y")
    assert [l.description for l in lines] == ["OK", "Bad"]  # 12,345 groups thousands
    assert [(p.row, p.message) for p in problems] == [
        (3, "'not a date' is not a date."),
        (4, "The line has no amount."),
        (6, "The line has too few columns."),
    ]


def test_columns_need_date_description_and_amounts() -> None:
    assert guess_columns(["Date", "Montant"]) is None
    assert guess_columns(["Libellé", "Montant"]) is None
    assert guess_columns(["Date", "Libellé", "Solde"]) is None


def test_ambiguous_dates_prefer_day_first() -> None:
    assert detect_date_format(["03/10/2026", "04/10/2026"]) == "%d/%m/%Y"
    assert detect_date_format(["10/31/2026"]) == "%m/%d/%Y"
    assert detect_date_format(["yesterday"]) is None
