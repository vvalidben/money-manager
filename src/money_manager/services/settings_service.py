"""Application settings: the base currency and application information.

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
from pathlib import Path

from money_manager import APP_NAME, __version__
from money_manager.core.errors import ConflictError
from money_manager.domain.currency import SUPPORTED_CURRENCIES, CurrencyInfo, validate_currency
from money_manager.domain.money import DEFAULT_CURRENCY
from money_manager.persistence.database import CREATED_AT_KEY, Database
from money_manager.persistence.migrator import current_revision
from money_manager.persistence.models import AppMetadata
from money_manager.persistence.repositories import AccountRepository, SettingRepository

logger = logging.getLogger(__name__)

CURRENCY_KEY = "currency"


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
                    "The currency can only be changed before any account exists, because "
                    "Money Manager never converts amounts between currencies.")
            SettingRepository(session).set(CURRENCY_KEY, json.dumps(currency))
        logger.info("Base currency set to %s", currency)
        return currency

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
