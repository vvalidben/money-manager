"""Shared guard for reports that add up money across accounts."""

from collections.abc import Iterable

from money_manager.core.errors import CurrencyMismatchError
from money_manager.persistence.models import AccountModel


def ensure_single_currency(accounts: Iterable[AccountModel], currency: str, report: str) -> None:
    for account in accounts:
        if account.currency != currency:
            raise CurrencyMismatchError(
                f"Account '{account.name}' uses {account.currency}; the {report} "
                f"reports in {currency}."
            )
