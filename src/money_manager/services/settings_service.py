"""Application settings: the base currency, animations and application information.

The currency can only change while no account exists: amounts are never
converted (there are no exchange rates), so switching the currency of
recorded money would silently change what the numbers mean. Services read
the currency when they are created; after a change the UI rebuilds them.
"""

import json
import logging
import platform
import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from money_manager import APP_NAME, __version__
from money_manager.core.errors import ConflictError, ValidationError
from money_manager.domain.currency import SUPPORTED_CURRENCIES, CurrencyInfo, validate_currency
from money_manager.domain.money import DEFAULT_CURRENCY
from money_manager.persistence.database import CREATED_AT_KEY, Database
from money_manager.persistence.migrator import current_revision
from money_manager.persistence.models import AppMetadata
from money_manager.persistence.repositories import AccountRepository, SettingRepository
from money_manager.core.i18n import CHOICES as LANGUAGE_CHOICES
from money_manager.core.i18n import DEFAULT_CHOICE as DEFAULT_LANGUAGE
from money_manager.core.i18n import tr

logger = logging.getLogger(__name__)

CURRENCY_KEY = "currency"
ANIMATIONS_KEY = "animations"
DAILY_COPIES_KEY = "daily_copies"
APP_LOCK_KEY = "app_lock"
LOCK_AFTER_KEY = "lock_after_minutes"
THEME_KEY = "theme"
UPDATE_CHECK_KEY = "update_check"
LANGUAGE_KEY = "language"
REMINDERS_KEY = "reminders"
KEEP_IN_TRAY_KEY = "keep_in_tray"
SHOWN_REMINDERS_KEY = "shown_reminders"
SHOWN_REMINDERS_KEPT_DAYS = 60
LAST_UPDATE_CHECK_KEY = "last_update_check"

LOCK_AFTER_CHOICES = (1, 5, 15, 30, 0)  # minutes without use; 0 = only when asked
DEFAULT_LOCK_AFTER = 5
THEMES = ("dark", "light", "system")  # "system" follows Windows' app mode
DEFAULT_THEME = "dark"


@dataclass(frozen=True, slots=True)
class ApplicationInfo:
    name: str
    version: str
    schema_revision: str
    database_path: Path | None
    database_created_at: str
    python_version: str
    sqlite_version: str


class SettingsService:
    def __init__(self, database: Database) -> None:
        self._database = database

    # ------------------------------------------------------------- currency

    @staticmethod
    def available_currencies() -> list[CurrencyInfo]:
        return list(SUPPORTED_CURRENCIES.values())

    def currency(self) -> str:
        """The stored currency; else that of existing accounts; else MAD."""
        with self._database.session() as session:
            stored = SettingRepository(session).get(CURRENCY_KEY)
            accounts = AccountRepository(session).list_all()
            account_currency = accounts[0].currency if accounts else None
        if stored is not None:
            try:
                return validate_currency(json.loads(stored))
            except (ValueError, TypeError):
                logger.warning("Ignoring an unreadable stored currency")
        return account_currency or DEFAULT_CURRENCY

    def can_change_currency(self) -> bool:
        with self._database.session() as session:
            return not AccountRepository(session).list_all()

    def set_currency(self, code: str) -> str:
        currency = validate_currency(code)
        with self._database.session() as session:
            accounts = AccountRepository(session).list_all()
            if accounts and any(a.currency != currency for a in accounts):
                raise ConflictError(
                    tr("The currency can only be changed before any account exists, because "
                    "Money Manager never converts amounts between currencies."))
            SettingRepository(session).set(CURRENCY_KEY, json.dumps(currency))
        logger.info("Base currency set to %s", currency)
        return currency

    # ----------------------------------------------------------- animations

    def animations_enabled(self) -> bool:
        """The user's choice; on unless switched off in Settings."""
        return self._flag(ANIMATIONS_KEY, "animations")

    def set_animations_enabled(self, enabled: bool) -> bool:
        return self._set_flag(ANIMATIONS_KEY, "Animations", enabled)

    # --------------------------------------------------------- daily copies

    def daily_copies_enabled(self) -> bool:
        """Whether a copy of the data is saved automatically each day (on by default)."""
        return self._flag(DAILY_COPIES_KEY, "daily copies")

    def set_daily_copies_enabled(self, enabled: bool) -> bool:
        return self._set_flag(DAILY_COPIES_KEY, "Daily copies", enabled)

    # ------------------------------------------------------------- app lock

    def app_lock_enabled(self) -> bool:
        """Whether Windows Hello is asked for on start and after idle time (off by default)."""
        return self._flag(APP_LOCK_KEY, "app lock", default=False)

    def set_app_lock_enabled(self, enabled: bool) -> bool:
        return self._set_flag(APP_LOCK_KEY, "App lock", enabled)

    def lock_after_minutes(self) -> int:
        """Minutes without use before the app locks itself; 0 = only when asked."""
        value = self._stored(LOCK_AFTER_KEY, "lock time")
        if isinstance(value, bool) or value not in LOCK_AFTER_CHOICES:
            return DEFAULT_LOCK_AFTER
        return value  # type: ignore[return-value]

    def set_lock_after_minutes(self, minutes: int) -> int:
        if isinstance(minutes, bool) or minutes not in LOCK_AFTER_CHOICES:
            raise ValidationError(tr("Choose one of the offered lock times."), "lock_after")
        with self._database.session() as session:
            SettingRepository(session).set(LOCK_AFTER_KEY, json.dumps(minutes))
        logger.info("Lock after %s minutes", minutes)
        return minutes

    # ---------------------------------------------------------------- theme

    def theme(self) -> str:
        """``dark``, ``light`` or ``system``."""
        value = self._stored(THEME_KEY, "theme")
        return value if value in THEMES else DEFAULT_THEME

    def set_theme(self, theme: str) -> str:
        if theme not in THEMES:
            raise ValidationError(tr("Choose dark, light or the Windows setting."), "theme")
        with self._database.session() as session:
            SettingRepository(session).set(THEME_KEY, json.dumps(theme))
        logger.info("Theme set to %s", theme)
        return theme

    # ------------------------------------------------------------- language

    def language(self) -> str:
        """``system`` (Windows' display language), ``en`` or ``fr``."""
        value = self._stored(LANGUAGE_KEY, "language")
        return value if value in LANGUAGE_CHOICES else DEFAULT_LANGUAGE

    def set_language(self, choice: str) -> str:
        if choice not in LANGUAGE_CHOICES:
            raise ValidationError(tr("Choose one of the offered languages."), "language")
        with self._database.session() as session:
            SettingRepository(session).set(LANGUAGE_KEY, json.dumps(choice))
        logger.info("Language set to %s", choice)
        return choice

    # ------------------------------------------------------------ reminders

    def reminders_enabled(self) -> bool:
        """Notifications for payments due, budgets, loans and a low forecast (on by default)."""
        return self._flag(REMINDERS_KEY, "reminders")

    def set_reminders_enabled(self, enabled: bool) -> bool:
        return self._set_flag(REMINDERS_KEY, "Reminders", enabled)

    def keep_in_tray(self) -> bool:
        """Closing the window keeps Money Manager in the notification area (off by default)."""
        return self._flag(KEEP_IN_TRAY_KEY, "keep in tray", default=False)

    def set_keep_in_tray(self, enabled: bool) -> bool:
        return self._set_flag(KEEP_IN_TRAY_KEY, "Keep in tray", enabled)

    def shown_reminders(self) -> dict[str, str]:
        """Reminder keys already shown, with the day they were shown (ISO)."""
        value = self._stored(SHOWN_REMINDERS_KEY, "shown reminders")
        if not isinstance(value, dict):
            return {}
        return {k: v for k, v in value.items() if isinstance(k, str) and isinstance(v, str)}

    def mark_reminders_shown(self, keys: list[str], today: date) -> None:
        """Remember ``keys``; entries older than ``SHOWN_REMINDERS_KEPT_DAYS`` are dropped."""
        shown = self.shown_reminders()
        cutoff = (today - timedelta(days=SHOWN_REMINDERS_KEPT_DAYS)).isoformat()
        shown = {k: v for k, v in shown.items() if v >= cutoff}
        shown.update({key: today.isoformat() for key in keys})
        with self._database.session() as session:
            SettingRepository(session).set(SHOWN_REMINDERS_KEY, json.dumps(shown))

    # -------------------------------------------------------------- updates

    def update_check_enabled(self) -> bool:
        """Whether to look for a newer version once a day (off by default)."""
        return self._flag(UPDATE_CHECK_KEY, "update check", default=False)

    def set_update_check_enabled(self, enabled: bool) -> bool:
        return self._set_flag(UPDATE_CHECK_KEY, "Update check", enabled)

    def last_update_check(self) -> date | None:
        value = self._stored(LAST_UPDATE_CHECK_KEY, "last update check")
        try:
            return date.fromisoformat(value) if isinstance(value, str) else None
        except ValueError:
            return None

    def set_last_update_check(self, day: date) -> None:
        with self._database.session() as session:
            SettingRepository(session).set(LAST_UPDATE_CHECK_KEY, json.dumps(day.isoformat()))

    # -------------------------------------------------------------- helpers

    def _stored(self, key: str, name: str) -> object:
        """The stored JSON value, or None when absent or unreadable."""
        with self._database.session() as session:
            stored = SettingRepository(session).get(key)
        if stored is None:
            return None
        try:
            return json.loads(stored)
        except ValueError:
            logger.warning("Ignoring an unreadable %s setting", name)
            return None

    def _flag(self, key: str, name: str, *, default: bool = True) -> bool:
        value = self._stored(key, name)
        if value is None:
            return default
        if not isinstance(value, bool):
            logger.warning("Ignoring an unreadable %s setting", name)
            return default
        return value

    def _set_flag(self, key: str, name: str, enabled: bool) -> bool:
        with self._database.session() as session:
            SettingRepository(session).set(key, json.dumps(bool(enabled)))
        logger.info("%s %s", name, "on" if enabled else "off")
        return bool(enabled)

    # ---------------------------------------------------------- information

    def application_info(self) -> ApplicationInfo:
        with self._database.session() as session:
            created = session.get(AppMetadata, CREATED_AT_KEY)
            created_at = created.value if created is not None else ""
        return ApplicationInfo(
            name=APP_NAME,
            version=__version__,
            schema_revision=current_revision(self._database.engine) or "unknown",
            database_path=self._database.path,
            database_created_at=created_at,
            python_version=platform.python_version(),
            sqlite_version=sqlite3.sqlite_version,
        )
