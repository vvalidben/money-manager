"""Export, import and reset of all user data.

**Backup file** (``*.json``): every row of every table, exactly as stored
(integer minor units, ISO dates), with the schema revision and a SHA-256
checksum. It is the lossless export: importing it recreates the same data,
IDs and relationships included. API keys are never in the database, so they
are never exported.

**Import** replaces all current data with a backup. The file is fully
validated first (format, known schema revision, checksum, tables, columns
and value types). The current database is copied to a safety backup, then all
rows are replaced in *one* transaction, and foreign keys are checked before
committing; any failure rolls everything back, so data is never half-imported.

**Transactions CSV** is a read-only export for spreadsheets.

**Reset** deletes all data only when the caller passes the exact
confirmation word, after writing a safety backup.
"""

import csv
import hashlib
import json
import logging
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import Table, delete, insert, select, text
from sqlalchemy.orm import aliased

from money_manager import __version__
from money_manager.ai.secrets import ANTHROPIC_KEY_NAME, SecretStore
from money_manager.core.errors import DatabaseError, MoneyManagerError, ValidationError
from money_manager.domain.enums import TransactionType
from money_manager.domain.money import Money
from money_manager.persistence.base import Base
from money_manager.persistence.database import Database
from money_manager.persistence.migrator import current_revision, known_revisions
from money_manager.persistence.models import (
    AccountModel,
    AllocationModel,
    CategoryModel,
    TransactionModel,
)
from money_manager.services.allocation_service import ConsistencyReport

logger = logging.getLogger(__name__)

BACKUP_FORMAT = "money-manager-backup"
BACKUP_FORMAT_VERSION = 1
MAX_BACKUP_BYTES = 200 * 1024 * 1024
RESET_CONFIRMATION = "RESET"
# Internal bookkeeping about the database file itself (creation date, etc.).
EXCLUDED_TABLES = frozenset({"app_metadata"})
# Leading characters that make spreadsheet programs evaluate a cell as a formula.
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def data_tables() -> list[Table]:
    """Every table holding user data, parents before children."""
    return [t for t in Base.metadata.sorted_tables if t.name not in EXCLUDED_TABLES]


@dataclass(frozen=True, slots=True)
class BackupSummary:
    path: Path
    exported_at: str
    app_version: str
    schema_revision: str
    currency: str | None
    counts: Mapping[str, int] = field(default_factory=dict)

    @property
    def total_rows(self) -> int:
        return sum(self.counts.values())

    def count(self, table: str) -> int:
        return self.counts.get(table, 0)


@dataclass(frozen=True, slots=True)
class ImportResult:
    summary: BackupSummary
    safety_backup: Path | None
    consistency: ConsistencyReport | None = None


@dataclass(frozen=True, slots=True)
class ResetResult:
    safety_backup: Path | None
    api_key_removed: bool


class DataService:
    def __init__(self, database: Database, *, secret_store: SecretStore,
                 check_consistency: Callable[[], ConsistencyReport] | None = None) -> None:
        self._database = database
        self._secrets = secret_store
        # The allocation service's invariant check, run after an import.
        self._check_consistency = check_consistency

    # ---------------------------------------------------------------- export

    def export_backup(self, path: Path) -> BackupSummary:
        """Write every table to ``path`` atomically, then read it back to verify."""
        path = _path(path)
        tables: dict[str, dict[str, Any]] = {}
        with self._database.session() as session:
            for table in data_tables():
                columns = [c.name for c in table.columns]
                rows = session.execute(select(table).order_by(*table.primary_key.columns))
                tables[table.name] = {
                    "columns": columns,
                    "rows": [[_dump(row._mapping[name]) for name in columns] for row in rows],
                }
            currency = _currency_of(tables)
        document = {
            "format": BACKUP_FORMAT,
            "format_version": BACKUP_FORMAT_VERSION,
            "app_version": __version__,
            "schema_revision": current_revision(self._database.engine),
            "exported_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "currency": currency,
            "checksum": _checksum(tables),
            "tables": tables,
        }
        _write_atomically(path, json.dumps(document, ensure_ascii=False, indent=1))
        summary = self.read_backup(path)
        expected = {name: len(content["rows"]) for name, content in tables.items()}
        if dict(summary.counts) != expected:
            raise DatabaseError("The backup could not be verified after writing it.")
        logger.info("Exported a backup with %d rows", summary.total_rows)
        return summary

    def export_transactions_csv(self, path: Path) -> int:
        """All transactions as CSV (UTF-8 with BOM for spreadsheet programs)."""
        allocation = aliased(AllocationModel)
        stmt = (select(TransactionModel, AccountModel.name, CategoryModel.name, allocation.name)
                .join(AccountModel, TransactionModel.account_id == AccountModel.id)
                .outerjoin(CategoryModel, TransactionModel.category_id == CategoryModel.id)
                .outerjoin(allocation, TransactionModel.allocation_id == allocation.id)
                .order_by(TransactionModel.occurred_on, TransactionModel.id))
        with self._database.session() as session:
            rows = session.execute(stmt).all()
        lines: list[list[str]] = [["Date", "Type", "Account", "Category", "Allocation",
                                   "Amount", "Currency", "Description", "Notes"]]
        for model, account, category, allocation_name in rows:
            kind = TransactionType(model.type)
            amount = Money.from_minor_units(model.amount_minor * kind.sign, model.currency)
            lines.append([model.occurred_on.isoformat(), kind.label, _cell(account),
                          _cell(category or ""), _cell(allocation_name or ""),
                          str(amount.amount), model.currency, _cell(model.description),
                          _cell(model.notes)])
        target = _path(path)
        temporary = target.with_name(target.name + ".tmp")
        try:
            with temporary.open("w", encoding="utf-8-sig", newline="") as handle:
                csv.writer(handle).writerows(lines)
            os.replace(temporary, target)
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            raise ValidationError(f"Could not write the file: {exc.strerror or exc}",
                                  "path") from exc
        logger.info("Exported %d transactions to CSV", len(rows))
        return len(rows)

    # ---------------------------------------------------------------- import

    def read_backup(self, path: Path) -> BackupSummary:
        """Validate a backup file completely without changing anything."""
        path = _path(path)
        document = _load_document(path)
        tables = document["tables"]
        return BackupSummary(
            path=path,
            exported_at=str(document.get("exported_at", "")),
            app_version=str(document.get("app_version", "")),
            schema_revision=str(document["schema_revision"]),
            currency=document.get("currency") if isinstance(document.get("currency"), str)
            else None,
            counts={name: len(content["rows"]) for name, content in tables.items()},
        )

    def import_backup(self, path: Path) -> ImportResult:
        """Replace all data with the backup (after a safety copy); all or nothing."""
        path = _path(path)
        document = _load_document(path)
        summary = self.read_backup(path)
        converted = {table.name: _rows_for(table, document["tables"][table.name])
                     for table in data_tables()}
        safety = self._database.backup("before-import")
        try:
            with self._database.session() as session:
                for table in reversed(data_tables()):
                    session.execute(delete(table))
                for table in data_tables():
                    rows = converted[table.name]
                    if rows:
                        session.execute(insert(table), rows)
                violations = session.execute(text("PRAGMA foreign_key_check")).fetchall()
                if violations:
                    raise ValidationError("The backup's records do not fit together (broken "
                                          "references). Nothing was imported.")
        except DatabaseError as exc:
            raise ValidationError("The backup could not be imported; your data was not "
                                  "changed.") from exc
        logger.info("Imported a backup with %d rows", summary.total_rows)
        report = self._check_consistency() if self._check_consistency is not None else None
        return ImportResult(summary, safety, report)

    # ----------------------------------------------------------------- reset

    def reset(self, confirmation: str, *, remove_api_key: bool = False) -> ResetResult:
        """Delete all data. Requires ``confirmation`` to be exactly ``RESET``."""
        if confirmation != RESET_CONFIRMATION:
            raise ValidationError(f"Type {RESET_CONFIRMATION} to confirm.", "confirmation")
        safety = self._database.backup("before-reset")
        with self._database.session() as session:
            for table in reversed(data_tables()):
                session.execute(delete(table))
        removed = False
        if remove_api_key:
            try:
                self._secrets.delete(ANTHROPIC_KEY_NAME)
                removed = True
            except MoneyManagerError as exc:
                logger.warning("Data was reset but the API key could not be removed: %s", exc)
        logger.info("All application data was reset")
        return ResetResult(safety, removed)


# ---------------------------------------------------------------- helpers


def _path(value: object) -> Path:
    if isinstance(value, str) and value.strip():
        return Path(value)
    if isinstance(value, os.PathLike) and not isinstance(value, bool):
        return Path(value)
    raise ValidationError("Choose a file.", "path")


def _dump(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(f"Unsupported value type {type(value).__name__}")


def _checksum(tables: Mapping[str, Any]) -> str:
    canonical = json.dumps(tables, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _currency_of(tables: Mapping[str, Any]) -> str | None:
    """The stored currency setting, else the accounts' currency."""
    settings = tables.get("settings", {})
    names = settings.get("columns", [])
    if "key" in names and "value" in names:
        key_at, value_at = names.index("key"), names.index("value")
        for row in settings.get("rows", []):
            if row[key_at] == "currency":
                try:
                    return str(json.loads(row[value_at]))
                except ValueError:
                    break
    accounts = tables.get("accounts", {})
    columns = accounts.get("columns", [])
    if "currency" in columns and accounts.get("rows"):
        return accounts["rows"][0][columns.index("currency")]
    return None


def _write_atomically(path: Path, content: str) -> None:
    temporary = path.with_name(path.name + ".tmp")
    try:
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, path)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise ValidationError(f"Could not write the file: {exc.strerror or exc}", "path") from exc


def _cell(value: str) -> str:
    """Neutralise text a spreadsheet would run as a formula."""
    return "'" + value if value.startswith(_FORMULA_PREFIXES) else value


def _invalid(detail: str) -> ValidationError:
    return ValidationError(f"This is not a valid Money Manager backup: {detail}", "path")


def _load_document(path: Path) -> dict[str, Any]:
    try:
        if path.stat().st_size > MAX_BACKUP_BYTES:
            raise _invalid("the file is too large.")
        document = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValidationError(f"Could not read the file: {exc.strerror or exc}", "path") from exc
    except (ValueError, UnicodeDecodeError) as exc:
        raise _invalid("the file is not readable JSON.") from exc
    if not isinstance(document, dict) or document.get("format") != BACKUP_FORMAT:
        raise _invalid("the file was not exported by Money Manager.")
    if document.get("format_version") != BACKUP_FORMAT_VERSION:
        raise _invalid("the backup format version is not supported.")
    # Any known schema whose tables and columns match (checked below) can be
    # imported; revisions that only add indexes do not change the data.
    if document.get("schema_revision") not in known_revisions():
        raise ValidationError(
            "This backup was made with a newer version of Money Manager (data schema "
            f"{document.get('schema_revision')}). Update Money Manager to import it.", "path")
    tables = document.get("tables")
    if not isinstance(tables, dict):
        raise _invalid("it contains no tables.")
    expected = {t.name for t in data_tables()}
    if set(tables) != expected:
        raise _invalid("its tables do not match this version of Money Manager.")
    if document.get("checksum") != _checksum(tables):
        raise _invalid("the file is damaged or was edited (checksum mismatch).")
    for table in data_tables():
        content = tables[table.name]
        if (not isinstance(content, dict) or not isinstance(content.get("rows"), list)
                or not isinstance(content.get("columns"), list)
                or sorted(content["columns"]) != sorted(c.name for c in table.columns)):
            raise _invalid(f"the table '{table.name}' does not have the expected columns.")
    return document


def _rows_for(table: Table, content: Mapping[str, Any]) -> list[dict[str, Any]]:
    columns: list[str] = content["columns"]
    rows = []
    for raw in content["rows"]:
        if not isinstance(raw, list) or len(raw) != len(columns):
            raise _invalid(f"a row in '{table.name}' is malformed.")
        rows.append({name: _load(table, name, value) for name, value in zip(columns, raw,
                                                                            strict=True)})
    return rows


def _load(table: Table, name: str, value: Any) -> Any:
    column = table.columns[name]
    if value is None:
        if not column.nullable:
            raise _invalid(f"'{table.name}.{name}' is missing a value.")
        return None
    expected = column.type.python_type
    try:
        if expected is bool and isinstance(value, bool):
            return value
        if expected is int and isinstance(value, int) and not isinstance(value, bool):
            return value
        if expected is str and isinstance(value, str):
            return value
        if expected is datetime and isinstance(value, str):
            return datetime.fromisoformat(value)
        if expected is date and isinstance(value, str):
            return date.fromisoformat(value)
    except ValueError:
        pass
    raise _invalid(f"'{table.name}.{name}' has a value of the wrong type.")
