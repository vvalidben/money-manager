"""Constants and types shared by the service tests."""

from collections.abc import Callable
from datetime import date

from money_manager.domain.entities import Transaction

TODAY = date(2026, 6, 15)
OPENING_DATE = date(2026, 1, 1)

AddTransaction = Callable[..., Transaction]


def fixed_today() -> date:
    return TODAY
