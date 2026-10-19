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

**Safety copies** are the database copies written next to the database before
a reset, an import, a restore or a schema upgrade, plus one automatic copy a
day (the newest ``DAILY_COPIES_KEPT`` are kept). Restoring one replaces all
current data the same way as an import (after a safety copy of the current
data, in one transaction); a copy from an older version is upgraded first, in
a temporary folder, so the copy itself is never changed.
"""

import csv
import hashlib
import json
import logging
import os
import re
import shutil
import sqlite3
import tempfile
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
    AccountTransferModel,
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
SAFETY_REASONS = {
    "before-reset": "Before a reset",
    "before-import": "Before importing a backup",
    "before-restore": "Before restoring a safety copy",
    "daily": "Daily automatic copy",
}
DAILY_REASON = "daily"
DAILY_COPIES_KEPT = 30
_SAFETY_NAME = re.compile(r"^(?P<stem>.+)\.backup-(?P<reason>.+)-(?P<stamp>\d{8}T\d{6}Z)\.db$")
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
class SafetyCopy:
    path: Path
    reason: str  # "before-reset", "before-import", "before-restore", or a schema revision
    created_at: datetime  # UTC, from the file name
    size_bytes: int
    accounts: int | None  # None when the copy cannot be read
    transactions: int | None

    @property
    def readable(self) -> bool:
        return self.accounts is not None

    @property
    def reason_text(self) -> str:
        return SAFETY_REASONS.get(self.reason, "Before an update of Money Manager")


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
            transfer_sides = {}
            for model in session.scalars(select(AccountTransferModel)):
                transfer_sides[model.out_transaction_id] = "Transfer out"
                transfer_sides[model.in_transaction_id] = "Transfer in"
        lines: list[list[str]] = [["Date", "Type", "Account", "Category", "Allocation",
                                   "Amount", "Currency", "Description", "Notes"]]
        for model, account, category, allocation_name in rows:
            kind = TransactionType(model.type)
            amount = Money.from_minor_units(model.amount_minor * kind.sign, model.currency)
            label = transfer_sides.get(model.id, kind.label)
            lines.append([model.occurred_on.isoformat(), label, _cell(account),
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
        safety = self._replace_all(converted, "before-import", "backup", "imported")
        logger.info("Imported a backup with %d rows", summary.total_rows)
        report = self._check_consistency() if self._check_consistency is not None else None
        return ImportResult(summary, safety, report)

    def _replace_all(self, converted: Mapping[str, list[dict[str, Any]]], label: str,
                     source: str, verb: str) -> Path | None:
        """Safety copy, then every row replaced in one transaction (all or nothing)."""
        safety = self._database.backup(label)
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
                    raise ValidationError(f"The {source}'s records do not fit together (broken "
                                          f"references). Nothing was {verb}.")
        except DatabaseError as exc:
            raise ValidationError(f"The {source} could not be {verb}; your data was not "
                                  "changed.") from exc
        return safety

    # --------------------------------------------------------- safety copies

    def safety_copies(self) -> list[SafetyCopy]:
        """The safety copies next to the database, newest first."""
        database_path = self._database.path
        if database_path is None or not database_path.parent.is_dir():
            return []
        copies = []
        for path in database_path.parent.glob(f"{database_path.stem}.backup-*.db"):
            match = _SAFETY_NAME.match(path.name)
            if match is None or match.group("stem") != database_path.stem:
                continue
            created = datetime.strptime(match.group("stamp"), "%Y%m%dT%H%M%SZ").replace(
                tzinfo=UTC)
            accounts, transactions = _peek_counts(path)
            copies.append(SafetyCopy(path, match.group("reason"), created, path.stat().st_size,
                                     accounts, transactions))
        copies.sort(key=lambda copy: (copy.created_at, copy.path.name), reverse=True)
        return copies

    def restore_safety_copy(self, path: Path) -> ImportResult:
        """Replace all data with a safety copy (after a safety copy of the current data)."""
        path = _path(path)
        known = {copy.path.resolve(): copy for copy in self.safety_copies()}
        copy = known.get(path.resolve())
        if copy is None:
            raise ValidationError("Choose one of the safety copies listed.", "path")
        converted, revision = _read_copy(copy.path)
        safety = self._replace_all(converted, "before-restore", "safety copy", "restored")
        counts = {name: len(rows) for name, rows in converted.items()}
        summary = BackupSummary(path=copy.path, exported_at=copy.created_at.isoformat(),
                                app_version="", schema_revision=revision,
                                currency=None, counts=counts)
        logger.info("Restored the safety copy %s (%d rows)", copy.path.name, summary.total_rows)
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


# ---------------------------------------------------------- daily copies


def ensure_daily_copy(database: Database, keep: int = DAILY_COPIES_KEPT,
                      now: datetime | None = None) -> Path | None:
    """Write today's automatic copy unless there is one (or no data yet), then keep
    only the newest ``keep`` daily copies. Returns the new copy, if one was written."""
    database_path = database.path
    if database_path is None or not database_path.exists():
        return None
    moment = (now or datetime.now(UTC)).astimezone()
    dailies = _daily_copies(database_path)
    if any(created.astimezone().date() == moment.date() for created, _ in dailies):
        return None
    with database.session() as session:
        has_data = session.execute(select(AccountModel.id).limit(1)).first() is not None
    if not has_data:
        return None
    copy = database.backup(DAILY_REASON)
    for _created, old in _daily_copies(database_path)[keep:]:
        try:
            old.unlink()
        except OSError:
            logger.warning("Could not remove the old daily copy %s", old.name)
    if copy is not None:
        logger.info("Wrote the daily copy %s", copy.name)
    return copy


def _daily_copies(database_path: Path) -> list[tuple[datetime, Path]]:
    """Daily copies next to the database, newest first."""
    found = []
    for path in database_path.parent.glob(f"{database_path.stem}.backup-{DAILY_REASON}-*.db"):
        match = _SAFETY_NAME.match(path.name)
        if match is None or match.group("reason") != DAILY_REASON:
            continue
        created = datetime.strptime(match.group("stamp"), "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
        found.append((created, path))
    found.sort(reverse=True)
    return found


# ---------------------------------------------------------------- helpers


def _peek_counts(path: Path) -> tuple[int | None, int | None]:
    """Accounts and transactions in a copy, read-only; (None, None) if unreadable."""
    try:
        connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        try:
            accounts = connection.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
            transactions = connection.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        finally:
            connection.close()
    except sqlite3.Error:
        return None, None
    return int(accounts), int(transactions)


def _read_copy(path: Path) -> tuple[dict[str, list[dict[str, Any]]], str]:
    """Every data row of a safety copy, upgraded to the current schema if needed.

    The copy is duplicated into a temporary folder first, so it is never changed."""
    with tempfile.TemporaryDirectory(prefix="money-manager-restore-") as folder:
        working = Path(folder) / "copy.db"
        try:
            shutil.copy2(path, working)
            check = sqlite3.connect(working)
            try:
                status = check.execute("PRAGMA integrity_check").fetchone()[0]
            finally:
                check.close()
        except (OSError, sqlite3.Error) as exc:
            raise ValidationError("This safety copy cannot be read.", "path") from exc
        if status != "ok":
            raise ValidationError("This safety copy is damaged and cannot be restored.", "path")
        database = Database(f"sqlite:///{working.as_posix()}")
        try:
            database.initialize()  # upgrades an older copy; refuses a newer one
            revision = current_revision(database.engine) or ""
            with database.session() as session:
                converted = {table.name: [dict(row._mapping) for row in session.execute(
                    select(table).order_by(*table.primary_key.columns))]
                    for table in data_tables()}
        except MoneyManagerError as exc:
            raise ValidationError(f"This safety copy cannot be restored: {exc}", "path") from exc
        finally:
            database.dispose()
    return converted, revision


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
