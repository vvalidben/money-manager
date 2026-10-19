"""Recurring entries: income or expenses recorded automatically on a schedule.

Unlike subscriptions (which wait for the user to confirm each payment), a
recurring entry records a real transaction by itself on each date — e.g. the
salary on the 1st or the rent on the 5th. Dates follow the subscription rules
(``domain.subscriptions.advance``): the day of the month is kept and clamped
to short months, weekly schedules add seven days.
"""

from dataclasses import dataclass
from datetime import date

from money_manager.domain.enums import TransactionType
from money_manager.domain.money import Money
from money_manager.domain.subscriptions import Frequency

RECURRING_TYPES = (TransactionType.INCOME, TransactionType.EXPENSE)
MAX_CATCH_UP = 60  # dates recorded per entry in one run (guards a long absence)
PAST_LIMIT_DAYS = 366  # a first date further back would record a flood of entries
FUTURE_LIMIT_YEARS = 5


@dataclass(frozen=True, slots=True)
class RecurringEntry:
    id: int
    description: str
    type: TransactionType  # income or expense
    amount: Money
    account_id: int
    category_id: int
    frequency: Frequency
    next_date: date  # the next date to record
    anchor_day: int
    is_active: bool


@dataclass(frozen=True, slots=True)
class RecordProblem:
    entry_id: int
    description: str
    due: date
    message: str


@dataclass(frozen=True, slots=True)
class RecordOutcome:
    recorded: int
    problems: tuple[RecordProblem, ...] = ()
