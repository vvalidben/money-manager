"""Shared guard for reports that add up money across accounts."""

from collections.abc import Iterable

from money_manager.core.errors import CurrencyMismatchError
from money_manager.persistence.models import AccountModel
from money_manager.core.i18n import tr


def ensure_single_currency(accounts: Iterable[AccountModel], currency: str, report: str) -> None:
    for account in accounts:
        if account.currency != currency:
            raise CurrencyMismatchError(
                tr("Account '{0}' uses {1}; the {2} reports in {3}.", account.name, account.currency, report, currency)
            )
