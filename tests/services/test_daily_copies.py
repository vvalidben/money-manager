"""The automatic daily copy: once a day, only with data, the newest 30 kept."""

from datetime import UTC, date, datetime, timedelta

from money_manager.persistence.database import Database
from money_manager.services import AppServices
from money_manager.services.data_service import DAILY_COPIES_KEPT, ensure_daily_copy

NOON = datetime(2026, 10, 19, 12, 0, tzinfo=UTC)


def test_nothing_to_copy_before_there_is_data(database: Database) -> None:
    assert ensure_daily_copy(database, now=NOON) is None


def test_one_copy_a_day(database: Database, app_services: AppServices) -> None:
    app_services.accounts.create("Bank", opening_balance="100", opening_date=date(2026, 1, 1))
    first = ensure_daily_copy(database, now=NOON)
    assert first is not None and first.is_file()
    assert ensure_daily_copy(database, now=NOON + timedelta(hours=3)) is None
    [copy] = app_services.data.safety_copies()
    assert copy.reason == "daily" and copy.reason_text == "Daily automatic copy"
    assert copy.accounts == 1


def test_only_the_newest_are_kept(database: Database, app_services: AppServices) -> None:
    app_services.accounts.create("Bank", opening_balance="100", opening_date=date(2026, 1, 1))
    assert database.path is not None
    for days in range(1, DAILY_COPIES_KEPT + 5):
        stamp = (NOON - timedelta(days=days)).strftime("%Y%m%dT%H%M%SZ")
        database.path.with_name(f"money_manager.backup-daily-{stamp}.db").write_bytes(b"old")
    other = database.path.with_name("money_manager.backup-before-reset-20200101T000000Z.db")
    other.write_bytes(b"kept")

    ensure_daily_copy(database, now=NOON)

    dailies = [c for c in app_services.data.safety_copies() if c.reason == "daily"]
    assert len(dailies) == DAILY_COPIES_KEPT
    assert dailies[0].accounts == 1  # today's real copy is the newest
    assert other.is_file()  # other safety copies are never pruned


def test_setting_defaults_on_and_persists(app_services: AppServices) -> None:
    assert app_services.settings.daily_copies_enabled() is True
    app_services.settings.set_daily_copies_enabled(False)
    assert app_services.settings.daily_copies_enabled() is False
