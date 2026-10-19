"""Immutable domain records returned by services and the inputs they accept."""

from dataclasses import dataclass
from datetime import date

from money_manager.domain.enums import CategoryKind, TransactionSort, TransactionType
from money_manager.domain.money import AmountInput, Money


@dataclass(frozen=True, slots=True)
class Account:
    id: int
    name: str
    currency: str
    opening_balance: Money
    opening_date: date


@dataclass(frozen=True, slots=True)
class Category:
    id: int
    name: str
    kind: CategoryKind
    is_archived: bool = False
    # Expense categories only: spending here is money invested, not consumed.
    is_investment: bool = False


@dataclass(frozen=True, slots=True)
class Transaction:
    id: int
    account_id: int
    type: TransactionType
    amount: Money  # always positive; ``type`` gives the direction
    occurred_on: date
    category_id: int | None
    description: str
    notes: str
    # Allocation the money was paid from / put into; None means Available.
    allocation_id: int | None = None

    @property
    def signed_amount(self) -> Money:
        """Effect on the balance: positive for inflows, negative for outflows."""
        return self.amount if self.type.sign > 0 else -self.amount


@dataclass(frozen=True, slots=True)
class AccountTransfer:
    """Money moved between two of the user's accounts (two linked adjustments)."""

    id: int
    from_account_id: int
    to_account_id: int
    amount: Money
    occurred_on: date
    description: str
    out_transaction_id: int
    in_transaction_id: int


@dataclass(frozen=True, slots=True)
class TransactionDraft:
    """Unvalidated input for creating or fully replacing a transaction."""

    account_id: int
    type: TransactionType | str
    amount: AmountInput
    occurred_on: date
    category_id: int | None = None
    description: str = ""
    notes: str = ""
    allocation_id: int | None = None


@dataclass(frozen=True, slots=True)
class TransactionFilter:
    """Optional criteria for listing transactions; dates are inclusive.

    ``search`` matches description, notes and category name (case-insensitive
    for ASCII letters) and, if it reads as an amount, the exact amount.
    """

    account_id: int | None = None
    category_id: int | None = None
    types: frozenset[TransactionType] | None = None
    start: date | None = None
    end: date | None = None
    allocation_id: int | None = None
    search: str = ""


@dataclass(frozen=True, slots=True)
class TransactionQuery:
    """A filtered, sorted page of transactions."""

    filters: TransactionFilter = TransactionFilter()
    sort: TransactionSort = TransactionSort.DATE
    descending: bool = True
    offset: int = 0
    limit: int = 50


@dataclass(frozen=True, slots=True)
class TransactionPage:
    items: tuple[Transaction, ...]
    total_count: int
    offset: int
    limit: int
    # Totals over *all* matching transactions, not only this page.
    income: Money
    expenses: Money

    @property
    def first_index(self) -> int:
        """1-based position of the first item, or 0 when the page is empty."""
        return self.offset + 1 if self.items else 0

    @property
    def last_index(self) -> int:
        return self.offset + len(self.items)

    @property
    def has_previous(self) -> bool:
        return self.offset > 0

    @property
    def has_next(self) -> bool:
        return self.last_index < self.total_count


@dataclass(frozen=True, slots=True)
class Allocation:
    """A user-named purpose that reserves part of the existing money."""

    id: int
    name: str
    is_archived: bool = False


@dataclass(frozen=True, slots=True)
class AllocationTransfer:
    """Money moved between allocations. ``None`` on either side means Available.

    A transfer never changes the real balance.
    """

    id: int
    from_allocation_id: int | None
    to_allocation_id: int | None
    amount: Money
    occurred_on: date
    note: str
