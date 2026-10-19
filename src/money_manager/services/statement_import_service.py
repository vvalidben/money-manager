"""Importing a bank statement (CSV) into one account.

Reading and parsing are pure (``domain.statement``). This service decodes the
file, marks lines already recorded in the account, and records the new ones as
income or expenses in one unit of work. Every line is validated like an entry
typed by hand; a line that cannot be recorded (e.g. dated before the account
was opened) is reported as a problem and the rest are recorded.

**Duplicates:** a line matches an existing transaction of the account with the
same date, signed amount and description (case and spacing ignored). Matches
are counted, so two identical coffees in the file and one already recorded
import one.
"""

import logging
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from money_manager.core.errors import ValidationError
from money_manager.domain.entities import TransactionDraft, TransactionFilter
from money_manager.domain.enums import TransactionType
from money_manager.domain.statement import (
    StatementColumns,
    StatementLine,
    StatementProblem,
    StatementTable,
    parse_statement,
    read_table,
)
from money_manager.domain.validation import MAX_DESCRIPTION_LENGTH, validate_id
from money_manager.persistence.database import Database
from money_manager.services.transaction_service import TransactionService

logger = logging.getLogger(__name__)

MAX_STATEMENT_BYTES = 20 * 1024 * 1024
ENCODINGS = ("utf-8-sig", "cp1252")  # Windows banks often export in cp1252


@dataclass(frozen=True, slots=True)
class PreviewLine:
    line: StatementLine
    duplicate: bool


@dataclass(frozen=True, slots=True)
class StatementPreview:
    lines: tuple[PreviewLine, ...]
    problems: tuple[StatementProblem, ...]

    @property
    def new_lines(self) -> list[StatementLine]:
        return [p.line for p in self.lines if not p.duplicate]

    @property
    def duplicate_count(self) -> int:
        return sum(1 for p in self.lines if p.duplicate)


@dataclass(frozen=True, slots=True)
class ImportOutcome:
    imported: int
    duplicates: int
    problems: tuple[StatementProblem, ...]


def _key(occurred_on: date, signed: Decimal, description: str) -> tuple[date, Decimal, str]:
    return occurred_on, signed.quantize(Decimal("0.01")), " ".join(description.split()).casefold()


class StatementImportService:
    def __init__(self, database: Database, transactions: TransactionService, *,
                 today: Callable[[], date] = date.today) -> None:
        self._database = database
        self._transactions = transactions
        self._today = today

    def read(self, path: Path) -> StatementTable:
        """The file's header and rows (separator and encoding detected)."""
        try:
            if path.stat().st_size > MAX_STATEMENT_BYTES:
                raise ValidationError("The file is too large for a bank statement.", "path")
            raw = path.read_bytes()
        except OSError as exc:
            raise ValidationError(f"Could not read the file: {exc.strerror or exc}",
                                  "path") from exc
        for encoding in ENCODINGS:
            try:
                text = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:  # pragma: no cover - cp1252 decodes almost anything
            raise ValidationError("The file's text encoding is not supported.", "path")
        table = read_table(text)
        if not table.header or not table.rows:
            raise ValidationError("The file has no lines to import.", "path")
        return table

    def preview(self, table: StatementTable, account_id: int, columns: StatementColumns,
                date_format: str) -> StatementPreview:
        """Every line, marked when it is already recorded in the account."""
        lines, problems = parse_statement(table, columns, date_format)
        recorded = self._recorded(validate_id(account_id, "account_id"), lines)
        preview = []
        for line in lines:
            key = _key(line.occurred_on, line.amount, line.description)
            duplicate = recorded[key] > 0
            if duplicate:
                recorded[key] -= 1
            preview.append(PreviewLine(line, duplicate))
        return StatementPreview(tuple(preview), tuple(problems))

    def import_lines(self, account_id: int, lines: Sequence[StatementLine], *,
                     expense_category_id: int, income_category_id: int,
                     source: str = "") -> ImportOutcome:
        """Record the lines not yet in the account; report the ones that cannot be."""
        account_id = validate_id(account_id, "account_id")
        recorded = self._recorded(account_id, lines)
        note = f"Imported from {source}" if source else "Imported from a bank statement"
        imported, duplicates = 0, 0
        problems: list[StatementProblem] = []
        with self._database.session() as session:
            for line in lines:
                key = _key(line.occurred_on, line.amount, line.description)
                if recorded[key] > 0:
                    recorded[key] -= 1
                    duplicates += 1
                    continue
                income = line.amount > 0
                draft = TransactionDraft(
                    account_id,
                    TransactionType.INCOME if income else TransactionType.EXPENSE,
                    abs(line.amount),
                    line.occurred_on,
                    income_category_id if income else expense_category_id,
                    description=line.description[:MAX_DESCRIPTION_LENGTH],
                    notes=note,
                )
                try:
                    self._transactions.create_in_session(session, draft)
                except ValidationError as exc:  # raised before anything is added
                    problems.append(StatementProblem(line.row, str(exc)))
                    continue
                imported += 1
        logger.info("Imported %d statement lines (%d already recorded, %d problems)",
                    imported, duplicates, len(problems))
        return ImportOutcome(imported, duplicates, tuple(problems))

    def _recorded(self, account_id: int,
                  lines: Sequence[StatementLine]) -> Counter[tuple[date, Decimal, str]]:
        if not lines:
            return Counter()
        existing = self._transactions.list(TransactionFilter(
            account_id=account_id,
            start=min(line.occurred_on for line in lines),
            end=max(line.occurred_on for line in lines)))
        return Counter(_key(t.occurred_on, t.signed_amount.amount, t.description)
                       for t in existing)
