"""Currency settings, application information, export, import and reset."""

import csv
import json
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import select

from money_manager.ai.secrets import ANTHROPIC_KEY_NAME, MemorySecretStore
from money_manager.ai.settings import AIMode, AISettings
from money_manager.core.errors import ConflictError, ValidationError
from money_manager.domain.entities import TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.insights import InsightKind
from money_manager.domain.money import Money
from money_manager.persistence.database import Database
from money_manager.persistence.migrator import head_revision
from money_manager.services import AppServices
from money_manager.services.data_service import (
    BACKUP_FORMAT,
    RESET_CONFIRMATION,
    _checksum,
    data_tables,
)
from tests.ai.support import TEST_KEY, ScriptedProvider
from tests.services.support import fixed_today

TODAY = fixed_today()


def build(database: Database, store: MemorySecretStore | None = None) -> AppServices:
    return AppServices.create(database, today=fixed_today,
                              secret_store=store or MemorySecretStore(), environ={})


def snapshot(database: Database) -> dict[str, list[tuple[Any, ...]]]:
    """Every row of every data table, in primary-key order."""
    with database.session() as session:
        return {table.name: [tuple(row) for row in session.execute(
                    select(table).order_by(*table.primary_key.columns))]
                for table in data_tables()}


@pytest.fixture
def store() -> MemorySecretStore:
    return MemorySecretStore()


@pytest.fixture
def services(database: Database, store: MemorySecretStore) -> AppServices:
    return build(database, store)


@pytest.fixture
def everything(services: AppServices, monkeypatch: pytest.MonkeyPatch,
               tmp_path_factory: pytest.TempPathFactory) -> AppServices:
    """At least one row in every table, with private text and a stored API key."""
    s = services
    s.settings.set_currency("MAD")
    bank = s.accounts.create("Bank", opening_balance="10000.55", opening_date=date(2026, 1, 1))
    salary = s.categories.create("Salary", CategoryKind.INCOME)
    food = s.categories.create("Food", CategoryKind.EXPENSE)
    stocks = s.categories.create("Stocks", CategoryKind.EXPENSE)
    s.categories.set_investment(stocks.id, True)
    holiday = s.allocations.create("Holiday", initial_amount="1500")
    s.transactions.create(TransactionDraft(bank.id, TransactionType.INCOME, "12000",
                                           date(2026, 6, 1), salary.id, description="Salary"))
    s.transactions.create(TransactionDraft(bank.id, TransactionType.EXPENSE, "250.75",
                                           date(2026, 6, 3), food.id,
                                           description="=HYPERLINK(\"http://x\")",
                                           notes="café, «notes»", allocation_id=holiday.id))
    s.transactions.create(TransactionDraft(bank.id, TransactionType.ADJUSTMENT_OUT, "0.01",
                                           date(2026, 6, 4), None, description="Rounding"))
    s.transfers.transfer(from_allocation_id=None, to_allocation_id=holiday.id, amount="100",
                         on=date(2026, 6, 5), note="top up")
    cash = s.accounts.create("Cash", opening_balance="0", opening_date=date(2026, 1, 1))
    s.account_transfers.create(bank.id, cash.id, "200", date(2026, 6, 5),
                               description="Cash for the market")
    s.budgets.set(food.id, "1800")
    s.category_rules.learn("CB MARJANE", food.id)
    s.recurring.create("Rent", type="expense", amount="3000", account_id=bank.id,
                       category_id=food.id, frequency="monthly",
                       first_date=date(2026, 7, 5))
    loan = s.debts.create("Loan to Sami", direction="lent", amount="700",
                          start_date=date(2026, 6, 2), account_id=bank.id)
    s.debts.record_payment(loan.id, "100", date(2026, 6, 9), account_id=bank.id)
    receipt = tmp_path_factory.mktemp("receipt") / "ticket.png"
    receipt.write_bytes(b"\x89PNG\r\n\x1a\n" + bytes(range(256)))
    s.receipts.add(s.transactions.list()[0].id, receipt)
    s.goals.create_with_new_allocation("Car", target="50000", deadline=date(2027, 6, 1),
                                       initial_amount="500")
    s.goals.create_manual("Gift", target="800", current="200")
    netflix = s.subscriptions.create("Netflix", amount="65", frequency="monthly",
                                     next_payment_date=date(2026, 6, 10), category_id=food.id,
                                     account_id=bank.id)
    s.subscriptions.record_payment(netflix.id, date(2026, 6, 10))
    etf = s.investments.create("ETF", "etf", notes="broker")
    s.investments.add_contribution(etf.investment.id, "1000", date(2026, 6, 6),
                                   account_id=bank.id, category_id=stocks.id)
    s.investments.add_contribution(etf.investment.id, "300", date(2026, 5, 1), note="outside")
    s.investments.set_value(etf.investment.id, "1350.20", date(2026, 6, 12))
    s.ai.save_settings(AISettings(AIMode.ONLINE))
    s.ai.save_api_key(TEST_KEY)
    fake = ScriptedProvider()
    monkeypatch.setattr(s.ai, "provider", lambda settings=None: fake)
    prepared = s.ai.prepare(kind=InsightKind.SPENDING)
    s.ai.record(prepared, s.ai.send(prepared))
    return s


# ---------------------------------------------------------------- currency


def test_currency_defaults_to_mad(services: AppServices) -> None:
    assert services.settings.currency() == "MAD" == services.base_currency
    codes = [c.code for c in services.settings.available_currencies()]
    assert codes[0] == "MAD" and {"EUR", "USD"} <= set(codes)


def test_currency_persists_and_applies_to_new_services(database: Database,
                                                      services: AppServices) -> None:
    assert services.settings.set_currency(" eur ") == "EUR"
    rebuilt = build(database)
    assert rebuilt.base_currency == "EUR" and rebuilt.settings.currency() == "EUR"
    account = rebuilt.accounts.create("Konto", opening_balance="10", opening_date=TODAY)
    assert account.currency == "EUR"


def test_currency_is_locked_once_accounts_exist(services: AppServices) -> None:
    services.accounts.create("Bank", opening_balance="0", opening_date=TODAY)
    assert not services.settings.can_change_currency()
    with pytest.raises(ConflictError, match="never converts"):
        services.settings.set_currency("USD")
    assert services.settings.set_currency("MAD") == "MAD"  # unchanged is fine
    assert services.settings.currency() == "MAD"


@pytest.mark.parametrize("code", ["", "XXX", "JPY", None, 12])
def test_unsupported_currencies(services: AppServices, code: object) -> None:
    with pytest.raises(ValidationError):
        services.settings.set_currency(code)  # type: ignore[arg-type]


def test_existing_accounts_decide_the_currency_without_a_setting(database: Database) -> None:
    eur = build(database, None)
    eur.settings.set_currency("EUR")
    build(database).accounts.create("Konto", opening_balance="1", opening_date=TODAY)
    with database.session() as session:
        from money_manager.persistence.repositories import SettingRepository
        SettingRepository(session).delete("currency")
    assert build(database).base_currency == "EUR"


def test_application_info(services: AppServices) -> None:
    info = services.settings.application_info()
    assert info.name == "Money Manager" and info.version
    assert info.schema_revision == head_revision()
    assert info.database_path is not None and info.database_path.name == "money_manager.db"
    assert info.database_created_at[:4].isdigit() and info.sqlite_version


# ------------------------------------------------------------------ export


def test_export_import_round_trip_loses_nothing(database: Database, everything: AppServices,
                                                tmp_path: Path) -> None:
    before = snapshot(database)
    assert all(before[t.name] for t in data_tables()), "fixture must fill every table"
    path = tmp_path / "backup.json"

    summary = everything.data.export_backup(path)
    everything.data.reset(RESET_CONFIRMATION)
    assert all(not rows for rows in snapshot(database).values())
    result = everything.data.import_backup(path)

    assert snapshot(database) == before
    assert summary.total_rows == sum(len(rows) for rows in before.values())
    assert result.consistency is not None and result.consistency.is_consistent
    rebuilt = build(database)
    assert rebuilt.balances.total_balance() == everything.balances.total_balance()


def test_backup_restores_into_another_database(everything: AppServices, database: Database,
                                               tmp_path: Path) -> None:
    path = tmp_path / "backup.json"
    everything.data.export_backup(path)
    other = Database(f"sqlite:///{(tmp_path / 'other.db').as_posix()}")
    other.initialize()
    try:
        build(other).data.import_backup(path)
        assert snapshot(other) == snapshot(database)
        assert build(other).base_currency == "MAD"
    finally:
        other.dispose()


def test_backup_file_format(everything: AppServices, tmp_path: Path) -> None:
    path = tmp_path / "backup.json"
    summary = everything.data.export_backup(path)
    document = json.loads(path.read_text(encoding="utf-8"))

    assert document["format"] == BACKUP_FORMAT and document["format_version"] == 1
    assert document["schema_revision"] == head_revision() == summary.schema_revision
    assert document["currency"] == "MAD" == summary.currency
    assert document["checksum"] == _checksum(document["tables"])
    assert "app_metadata" not in document["tables"]
    accounts = document["tables"]["accounts"]
    row = dict(zip(accounts["columns"], accounts["rows"][0], strict=True))
    assert row["opening_balance_minor"] == 1000055  # exact integer minor units
    assert row["opening_date"] == "2026-01-01"
    assert summary.count("transactions") == 9  # incl. subscription, contribution, transfer, loan
    assert not list(tmp_path.glob("*.tmp"))


def test_api_keys_are_never_exported(everything: AppServices, store: MemorySecretStore,
                                     tmp_path: Path) -> None:
    assert store.get(ANTHROPIC_KEY_NAME) == TEST_KEY
    path = tmp_path / "backup.json"
    everything.data.export_backup(path)
    assert TEST_KEY not in path.read_text(encoding="utf-8")


def test_transactions_csv(everything: AppServices, tmp_path: Path) -> None:
    path = tmp_path / "transactions.csv"
    count = everything.data.export_transactions_csv(path)

    raw = path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")  # BOM so spreadsheet programs read UTF-8
    rows = list(csv.reader(path.read_text(encoding="utf-8-sig").splitlines()))
    assert count == 9 and len(rows) == 10
    assert rows[0] == ["Date", "Type", "Account", "Category", "Allocation", "Amount",
                       "Currency", "Description", "Notes"]
    salary = next(r for r in rows if r[7] == "Salary")
    assert salary[5] == "12000.00" and salary[6] == "MAD"
    food = next(r for r in rows if r[3] == "Food" and r[4] == "Holiday")
    assert food[5] == "-250.75" and food[8] == "café, «notes»"
    assert food[7] == "'=HYPERLINK(\"http://x\")"  # not run as a formula
    assert next(r for r in rows if r[7] == "Rounding")[5] == "-0.01"
    transfer = sorted((r[1], r[2], r[5]) for r in rows if r[7] == "Cash for the market")
    assert transfer == [("Transfer in", "Cash", "200.00"), ("Transfer out", "Bank", "-200.00")]


# ------------------------------------------------------------------ import


def rewrite(path: Path, change: Any) -> Path:
    document = json.loads(path.read_text(encoding="utf-8"))
    change(document)
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def reseal(document: dict[str, Any]) -> None:
    document["checksum"] = _checksum(document["tables"])


def edit_first(table: str, column: str, value: Any) -> Any:
    def change(document: dict[str, Any]) -> None:
        content = document["tables"][table]
        content["rows"][0][content["columns"].index(column)] = value
        reseal(document)
    return change


@pytest.mark.parametrize(("change", "message"), [
    (lambda d: d["tables"]["accounts"]["rows"][0].__setitem__(1, "Edited"), "damaged"),
    (lambda d: d.update(format="something-else"), "not exported by Money Manager"),
    (lambda d: d.update(format_version=99), "format version"),
    (lambda d: d.update(schema_revision="9999"), "newer version"),
    (lambda d: (d["tables"].pop("goals"), reseal(d)), "tables do not match"),
    (lambda d: (d["tables"]["goals"]["columns"].pop(), reseal(d)), "expected columns"),
    (edit_first("accounts", "opening_balance_minor", "10000"), "wrong type"),
    (edit_first("accounts", "opening_balance_minor", 1.5), "wrong type"),
    (edit_first("accounts", "opening_date", "1st of June"), "wrong type"),
    (edit_first("accounts", "name", None), "missing a value"),
    (edit_first("transactions", "account_id", 999), "could not be imported"),
    (edit_first("transactions", "amount_minor", -5), "could not be imported"),
])
def test_invalid_backups_change_nothing(everything: AppServices, database: Database,
                                        tmp_path: Path, change: Any, message: str) -> None:
    path = tmp_path / "backup.json"
    everything.data.export_backup(path)
    everything.transactions.create(TransactionDraft(
        everything.accounts.list()[0].id, TransactionType.INCOME, "1", TODAY,
        everything.categories.list(CategoryKind.INCOME)[0].id, description="after export"))
    before = snapshot(database)

    with pytest.raises(ValidationError, match=message):
        everything.data.import_backup(rewrite(path, change))

    assert snapshot(database) == before


@pytest.mark.parametrize("content", [b"", b"not json", b"[1, 2]", b"\xff\xfe\x00"])
def test_unreadable_files(services: AppServices, tmp_path: Path, content: bytes) -> None:
    path = tmp_path / "bad.json"
    path.write_bytes(content)
    with pytest.raises(ValidationError, match="not a valid Money Manager backup"):
        services.data.read_backup(path)


def test_missing_file(services: AppServices, tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="Could not read the file"):
        services.data.read_backup(tmp_path / "missing.json")


def test_import_writes_a_safety_backup_first(everything: AppServices, database: Database,
                                             tmp_path: Path) -> None:
    path = tmp_path / "backup.json"
    everything.data.export_backup(path)
    result = everything.data.import_backup(path)
    assert result.safety_backup is not None and result.safety_backup.is_file()
    assert "before-import" in result.safety_backup.name
    with sqlite3.connect(result.safety_backup) as copy:
        assert copy.execute("SELECT count(*) FROM transactions").fetchone()[0] == 9


# ------------------------------------------------------------------- reset


@pytest.mark.parametrize("word", ["", "reset", "RESET ", "yes", "DELETE"])
def test_reset_needs_the_exact_word(everything: AppServices, database: Database,
                                    store: MemorySecretStore, word: str) -> None:
    before = snapshot(database)
    with pytest.raises(ValidationError, match="Type RESET"):
        everything.data.reset(word, remove_api_key=True)
    assert snapshot(database) == before
    assert store.get(ANTHROPIC_KEY_NAME) == TEST_KEY


def test_reset(everything: AppServices, database: Database, store: MemorySecretStore) -> None:
    result = everything.data.reset(RESET_CONFIRMATION)

    assert all(not rows for rows in snapshot(database).values())
    assert result.safety_backup is not None and "before-reset" in result.safety_backup.name
    with sqlite3.connect(result.safety_backup) as copy:
        assert copy.execute("SELECT count(*) FROM accounts").fetchone()[0] == 2
    assert store.get(ANTHROPIC_KEY_NAME) == TEST_KEY and not result.api_key_removed
    rebuilt = build(database, store)
    assert rebuilt.base_currency == "MAD" and rebuilt.ai.settings() == AISettings()
    assert rebuilt.balances.total_balance() == Money.zero()


def test_reset_can_remove_the_api_key(everything: AppServices,
                                      store: MemorySecretStore) -> None:
    assert everything.data.reset(RESET_CONFIRMATION, remove_api_key=True).api_key_removed
    assert store.get(ANTHROPIC_KEY_NAME) is None


def test_ai_configuration_survives_a_backup(everything: AppServices, database: Database,
                                            tmp_path: Path) -> None:
    everything.ai.save_settings(AISettings(AIMode.AUTO, local_model="llama3.2",
                                           timeout_seconds=45))
    path = tmp_path / "backup.json"
    everything.data.export_backup(path)
    everything.data.reset(RESET_CONFIRMATION)
    everything.data.import_backup(path)
    assert build(database).ai.settings() == AISettings(AIMode.AUTO, local_model="llama3.2",
                                                       timeout_seconds=45)
    assert [i.kind for i in build(database).ai.history()] == [InsightKind.SPENDING]


def test_backups_from_an_earlier_schema_with_the_same_tables_import(
    everything: AppServices, database: Database, tmp_path: Path,
) -> None:
    before = snapshot(database)
    path = tmp_path / "backup.json"
    everything.data.export_backup(path)
    rewrite(path, lambda d: d.update(schema_revision="0007"))  # before the index-only 0008

    everything.data.reset(RESET_CONFIRMATION)
    everything.data.import_backup(path)

    assert snapshot(database) == before



class TestPasswordProtectedBackups:
    def test_round_trip(self, everything: AppServices, database: Database,
                        tmp_path: Path) -> None:
        from money_manager.services.data_service import ENCRYPTED_MAGIC, BackupPasswordNeeded

        before = snapshot(database)
        path = tmp_path / "backup.mmbackup"
        everything.data.export_backup(path, password="correct horse")
        raw = path.read_bytes()
        assert raw.startswith(ENCRYPTED_MAGIC)
        assert b"Salary" not in raw and b"HYPERLINK" not in raw  # nothing readable
        assert everything.data.is_encrypted(path)
        with pytest.raises(BackupPasswordNeeded):
            everything.data.read_backup(path)
        with pytest.raises(ValidationError, match="password is wrong"):
            everything.data.read_backup(path, "wrong password")
        everything.data.reset(RESET_CONFIRMATION)
        everything.data.import_backup(path, "correct horse")
        assert snapshot(database) == before

    def test_tampering_and_short_passwords(self, everything: AppServices,
                                           tmp_path: Path) -> None:
        path = tmp_path / "backup.mmbackup"
        with pytest.raises(ValidationError, match="at least 8"):
            everything.data.export_backup(path, password="short")
        everything.data.export_backup(path, password="long enough")
        raw = bytearray(path.read_bytes())
        raw[-5] ^= 0x01
        path.write_bytes(bytes(raw))
        with pytest.raises(ValidationError, match="damaged"):
            everything.data.read_backup(path, "long enough")
        assert not everything.data.is_encrypted(tmp_path / "missing")
