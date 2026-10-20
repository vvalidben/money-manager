"""Reading bank statements exported as CSV (pure, deterministic).

Banks export statements in many shapes, so every step is tolerant but exact:

* the separator (``;``, ``,``, tab) is detected from the text;
* the date, description and amount columns are guessed from French and
  English headers (``Date``, ``Libellé``, ``Montant``, ``Débit``/``Crédit``,
  ``Amount``…) and can be chosen by hand;
* amounts may use either decimal separator and thousands grouping
  (``1 234,56``, ``1,234.56``, ``-12,50 DH``, ``(12.50)``); more than two
  decimals is a problem, never rounded;
* the date format is the first candidate that reads every date in the file.

Lines that cannot be read become problems with a reason; nothing is guessed.
"""

import csv
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from money_manager.core.i18n import tr

DATE_FORMATS = ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%Y/%m/%d",
                "%m/%d/%Y")
_DELIMITERS = ";,\t|"
_CURRENCY_WORDS = re.compile(r"(?i)\b(mad|dh|dhs|eur|usd|gbp)\b|[€$£]")

_DATE_WORDS = ("date operation", "date d operation", "date", "jour", "booking date")
_DESCRIPTION_WORDS = ("libelle", "description", "details", "detail", "label", "operation",
                      "narrative", "memo", "payee", "beneficiaire", "reference")
_AMOUNT_WORDS = ("montant", "amount", "somme")
_DEBIT_WORDS = ("debit", "withdrawal", "sortie", "paid out", "money out")
_CREDIT_WORDS = ("credit", "deposit", "entree", "paid in", "money in")


@dataclass(frozen=True, slots=True)
class StatementColumns:
    """Column positions; either ``amount`` or ``debit``/``credit`` is used."""

    date: int
    description: int
    amount: int | None = None
    debit: int | None = None
    credit: int | None = None

    @property
    def split_amounts(self) -> bool:
        return self.amount is None


@dataclass(frozen=True, slots=True)
class StatementLine:
    row: int  # 1-based line number in the file (the header is line 1)
    occurred_on: date
    description: str
    amount: Decimal  # signed: positive = money in


@dataclass(frozen=True, slots=True)
class StatementProblem:
    row: int
    message: str


@dataclass(frozen=True, slots=True)
class StatementTable:
    header: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]


def read_table(text: str) -> StatementTable:
    """The header and data rows of a CSV text (separator detected, blank rows dropped)."""
    sample = text[:4096]
    try:
        dialect: type[csv.Dialect] | csv.Dialect = csv.Sniffer().sniff(sample, _DELIMITERS)
    except csv.Error:
        counts = {d: sample.count(d) for d in _DELIMITERS}
        delimiter = max(counts, key=lambda d: counts[d])

        class _Simple(csv.excel):
            pass

        _Simple.delimiter = delimiter
        dialect = _Simple
    rows = [tuple(cell.strip() for cell in row)
            for row in csv.reader(text.splitlines(), dialect)]
    rows = [row for row in rows if any(row)]
    if not rows:
        return StatementTable((), ())
    return StatementTable(rows[0], tuple(rows[1:]))


def _plain(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    letters = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", letters.lower()).strip()


def _find(header: Sequence[str], words: Sequence[str], taken: set[int], *,
          dates: bool = False) -> int | None:
    """The first column matching the earliest word. Columns naming a date
    ("Date de valeur", "Value date") are only ever used as the date."""
    plain = [_plain(cell) for cell in header]
    for word in words:  # earlier words are preferred
        for index, cell in enumerate(plain):
            if index in taken or (not dates and "date" in cell.split()):
                continue
            if cell == word or cell.startswith(word + " ") or word in cell.split():
                return index
    return None


def guess_columns(header: Sequence[str]) -> StatementColumns | None:
    """Columns from the header's words, or None when date/description/amounts are missing."""
    taken: set[int] = set()
    date_at = _find(header, _DATE_WORDS, taken, dates=True)
    if date_at is None:
        return None
    taken.add(date_at)
    amount_at = _find(header, _AMOUNT_WORDS, taken)
    debit_at = credit_at = None
    if amount_at is not None:
        taken.add(amount_at)
    else:
        debit_at = _find(header, _DEBIT_WORDS, taken)
        if debit_at is not None:
            taken.add(debit_at)
        credit_at = _find(header, _CREDIT_WORDS, taken)
        if credit_at is not None:
            taken.add(credit_at)
        if debit_at is None and credit_at is None:
            return None
    description_at = _find(header, _DESCRIPTION_WORDS, taken)
    if description_at is None:
        return None
    return StatementColumns(date_at, description_at, amount_at, debit_at, credit_at)


def parse_amount(text: str) -> Decimal | None:
    """A signed amount from a bank's cell; None for an empty cell.

    Raises ValueError when the text is not an amount or has more than two decimals.
    """
    value = _CURRENCY_WORDS.sub("", text).replace(" ", "").replace(" ", "")
    value = value.replace(" ", "").replace("'", "").replace("−", "-")
    if not value:
        return None
    negative = False
    if value.startswith("(") and value.endswith(")"):
        negative, value = True, value[1:-1]
    if value.endswith("-"):
        negative, value = True, value[:-1]
    if value.startswith(("-", "+")):
        negative, value = negative or value[0] == "-", value[1:]
    if not re.fullmatch(r"[0-9.,]+", value) or not re.search(r"[0-9]", value):
        raise ValueError(tr("'{0}' is not an amount", text))
    last_dot, last_comma = value.rfind("."), value.rfind(",")
    if last_dot >= 0 and last_comma >= 0:
        decimal_mark = "." if last_dot > last_comma else ","
    elif last_dot >= 0 or last_comma >= 0:
        mark = "." if last_dot >= 0 else ","
        decimals = len(value) - value.rfind(mark) - 1
        # A lone separator followed by exactly three digits groups thousands (1.500 / 1,500).
        decimal_mark = None if value.count(mark) > 1 or decimals == 3 else mark
    else:
        decimal_mark = None
    grouping = {".", ","} - ({decimal_mark} if decimal_mark else set())
    for mark in grouping:
        value = value.replace(mark, "")
    if decimal_mark:
        value = value.replace(decimal_mark, ".")
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(tr("'{0}' is not an amount", text)) from exc
    if amount.as_tuple().exponent < -2:  # type: ignore[operator]
        raise ValueError(tr("'{0}' has more than two decimals", text))
    return -amount if negative else amount


def _date_text(text: str) -> str:
    return text.strip().split(" ")[0].split("T")[0]


def detect_date_format(values: Sequence[str]) -> str | None:
    """The first format that reads every non-empty date, or None."""
    dates = [_date_text(v) for v in values if v.strip()]
    if not dates:
        return None
    for fmt in DATE_FORMATS:
        try:
            for value in dates:
                datetime.strptime(value, fmt)
        except ValueError:
            continue
        return fmt
    return None


def parse_statement(table: StatementTable, columns: StatementColumns,
                    date_format: str) -> tuple[list[StatementLine], list[StatementProblem]]:
    """Every data row as a line, or as a problem saying why it cannot be used."""
    lines: list[StatementLine] = []
    problems: list[StatementProblem] = []
    needed = [i for i in (columns.date, columns.description, columns.amount, columns.debit,
                          columns.credit) if i is not None]
    for offset, row in enumerate(table.rows):
        number = offset + 2  # the header is line 1
        if len(row) <= max(needed):
            problems.append(StatementProblem(number, tr("The line has too few columns.")))
            continue
        try:
            occurred_on = datetime.strptime(_date_text(row[columns.date]), date_format).date()
        except ValueError:
            problems.append(StatementProblem(number, tr("'{0}' is not a date.", row[columns.date])))
            continue
        try:
            amount = _line_amount(row, columns)
        except ValueError as exc:
            problems.append(StatementProblem(number, f"{str(exc).capitalize()}."))
            continue
        if amount is None or amount == 0:
            problems.append(StatementProblem(number, tr("The line has no amount.")))
            continue
        description = " ".join(row[columns.description].split())
        lines.append(StatementLine(number, occurred_on, description, amount))
    return lines, problems


def _line_amount(row: Sequence[str], columns: StatementColumns) -> Decimal | None:
    if columns.amount is not None:
        return parse_amount(row[columns.amount])
    debit = parse_amount(row[columns.debit]) if columns.debit is not None else None
    credit = parse_amount(row[columns.credit]) if columns.credit is not None else None
    if debit is None and credit is None:
        return None
    # Banks write debits as positive or negative numbers; either way they are money out.
    return (abs(credit) if credit is not None else Decimal(0)) - (
        abs(debit) if debit is not None else Decimal(0))
