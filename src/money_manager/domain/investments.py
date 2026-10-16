"""Investment tracking (pure, deterministic, no market data).

Rules
-----
* An investment is a holding outside the tracked accounts. Its history is a
  list of contributions and withdrawals plus user-entered valuations.
* Net invested = contributions − withdrawals.
* Current value = the most recent valuation. There is no market data.
* A return is only calculated when it can be trusted: a valuation must exist
  and be dated on or after the latest contribution/withdrawal (otherwise the
  value is *out of date*). Then:
      profit = current value − net invested
      return = profit ÷ net invested   (only when net invested > 0)
  Ratios are exact ``Decimal`` rounded half-up to four places.
* A contribution may be backed by a real expense transaction (money left an
  account); its amount and date then come from that transaction, so the two
  can never disagree. External contributions (money from outside the app)
  store their own amount and date and never touch the balance.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from money_manager.domain.health import ratio
from money_manager.domain.money import Money, sum_money


class InvestmentKind(StrEnum):
    STOCK = "stock"
    ETF = "etf"
    CRYPTO = "crypto"
    GOLD = "gold"
    OTHER = "other"


class EntryKind(StrEnum):
    CONTRIBUTION = "contribution"
    WITHDRAWAL = "withdrawal"


@dataclass(frozen=True, slots=True)
class Investment:
    id: int
    name: str
    kind: InvestmentKind
    notes: str
    is_archived: bool = False


@dataclass(frozen=True, slots=True)
class InvestmentEntry:
    id: int
    investment_id: int
    kind: EntryKind
    amount: Money
    occurred_on: date
    note: str
    transaction_id: int | None = None  # set when paid from one of the user's accounts

    @property
    def signed_amount(self) -> Money:
        return self.amount if self.kind is EntryKind.CONTRIBUTION else -self.amount


@dataclass(frozen=True, slots=True)
class Valuation:
    id: int
    investment_id: int
    valued_on: date
    value: Money
    note: str


@dataclass(frozen=True, slots=True)
class InvestmentPosition:
    investment: Investment
    entries: tuple[InvestmentEntry, ...]  # oldest first
    valuations: tuple[Valuation, ...]  # oldest first
    currency: str

    @property
    def contributed(self) -> Money:
        return sum_money((e.amount for e in self.entries if e.kind is EntryKind.CONTRIBUTION),
                         self.currency)

    @property
    def withdrawn(self) -> Money:
        return sum_money((e.amount for e in self.entries if e.kind is EntryKind.WITHDRAWAL),
                         self.currency)

    @property
    def net_invested(self) -> Money:
        return self.contributed - self.withdrawn

    @property
    def latest_valuation(self) -> Valuation | None:
        if not self.valuations:
            return None
        return max(self.valuations, key=lambda v: (v.valued_on, v.id))

    @property
    def last_activity(self) -> date | None:
        return max((e.occurred_on for e in self.entries), default=None)

    @property
    def current_value(self) -> Money | None:
        latest = self.latest_valuation
        return None if latest is None else latest.value

    @property
    def is_value_current(self) -> bool:
        """A valuation exists and no money moved in or out after it."""
        latest, activity = self.latest_valuation, self.last_activity
        return latest is not None and (activity is None or latest.valued_on >= activity)

    @property
    def profit(self) -> Money | None:
        value = self.current_value
        if value is None or not self.is_value_current:
            return None
        return value - self.net_invested

    @property
    def return_ratio(self) -> Decimal | None:
        profit = self.profit
        if profit is None or not self.net_invested.is_positive():
            return None
        return ratio(profit, self.net_invested)


@dataclass(frozen=True, slots=True)
class KindShare:
    kind: InvestmentKind
    value: Money
    share: Decimal | None


@dataclass(frozen=True, slots=True)
class PortfolioSummary:
    positions: tuple[InvestmentPosition, ...]  # active investments
    total_balance: Money  # real balance of the accounts, for net worth
    currency: str

    @property
    def contributed(self) -> Money:
        return sum_money((p.contributed for p in self.positions), self.currency)

    @property
    def withdrawn(self) -> Money:
        return sum_money((p.withdrawn for p in self.positions), self.currency)

    @property
    def net_invested(self) -> Money:
        return self.contributed - self.withdrawn

    @property
    def valued(self) -> tuple[InvestmentPosition, ...]:
        return tuple(p for p in self.positions if p.current_value is not None)

    @property
    def total_value(self) -> Money:
        """Sum of the latest known values (investments never valued are not counted)."""
        return sum_money((p.current_value for p in self.valued if p.current_value is not None),
                         self.currency)

    @property
    def with_return(self) -> tuple[InvestmentPosition, ...]:
        return tuple(p for p in self.positions if p.profit is not None)

    @property
    def total_profit(self) -> Money | None:
        """Profit over the investments whose value is up to date; None if there are none."""
        if not self.with_return:
            return None
        return sum_money((p.profit for p in self.with_return if p.profit is not None),
                         self.currency)

    @property
    def return_ratio(self) -> Decimal | None:
        profit = self.total_profit
        invested = sum_money((p.net_invested for p in self.with_return), self.currency)
        if profit is None or not invested.is_positive():
            return None
        return ratio(profit, invested)

    @property
    def net_worth(self) -> Money:
        """Account balance plus known investment values (these never overlap)."""
        return self.total_balance + self.total_value

    @property
    def by_kind(self) -> tuple[KindShare, ...]:
        totals: defaultdict[InvestmentKind, Money] = defaultdict(lambda: Money.zero(self.currency))
        for position in self.valued:
            assert position.current_value is not None
            totals[position.investment.kind] = totals[position.investment.kind] + position.current_value
        total = self.total_value
        rows = [KindShare(kind, value, ratio(value, total) if total.is_positive() else None)
                for kind, value in totals.items()]
        rows.sort(key=lambda r: (-r.value.minor_units, r.kind.value))
        return tuple(rows)
