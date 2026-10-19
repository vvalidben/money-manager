"""Turns accounts and their balances into display text (pure presentation, no Qt).

Every amount comes from ``BalanceService``; this module only words and shares it.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from money_manager.domain.balance import BalanceBreakdown
from money_manager.domain.entities import Account
from money_manager.domain.health import ratio
from money_manager.domain.money import sum_money
from money_manager.ui.dashboard.view_model import StatView
from money_manager.ui.formatting import (
    format_date,
    format_money,
    format_percent,
    format_signed_money,
)


@dataclass(frozen=True, slots=True)
class AccountCardView:
    account_id: int
    name: str
    balance: str
    is_negative: bool
    share_fraction: Decimal  # of all positive balances, 0…1 (drawing only)
    share: str
    since: str
    activity: str


def account_cards(accounts: Sequence[Account],
                  breakdowns: dict[int, BalanceBreakdown]) -> tuple[AccountCardView, ...]:
    """Largest balance first; shares are of the money you have (positive balances)."""
    if not accounts:
        return ()
    currency = accounts[0].currency
    assets = sum_money((b.balance for b in breakdowns.values() if b.balance.is_positive()),
                       currency)
    cards = []
    for account in accounts:
        breakdown = breakdowns[account.id]
        balance = breakdown.balance
        share = ratio(balance, assets) if balance.is_positive() else None
        if balance.is_negative():
            share_text = "Owed"
        elif share is None:
            share_text = "Empty"
        else:
            share_text = f"{format_percent(share)} of what you have"
        adjustments = breakdown.adjustments_in - breakdown.adjustments_out
        activity = (f"Since the start: in {format_money(breakdown.income)} · "
                    f"out {format_money(breakdown.expenses)}"
                    + ("" if adjustments.is_zero()
                       else f" · adjustments and transfers {format_signed_money(adjustments)}"))
        cards.append(AccountCardView(
            account_id=account.id,
            name=account.name,
            balance=format_money(balance),
            is_negative=balance.is_negative(),
            share_fraction=min(max(share or Decimal(0), Decimal(0)), Decimal(1)),
            share=share_text,
            since=(f"Tracked since {format_date(account.opening_date)} · opening balance "
                   f"{format_money(account.opening_balance)}"),
            activity=activity,
        ))
    cards.sort(key=lambda c: -breakdowns[c.account_id].balance.amount)
    return tuple(cards)


def summary_stats(breakdowns: dict[int, BalanceBreakdown], currency: str) -> tuple[StatView, ...]:
    balances = [b.balance for b in breakdowns.values()]
    total = sum_money(balances, currency)
    assets = sum_money((b for b in balances if b.is_positive()), currency)
    owed = sum_money((-b for b in balances if b.is_negative()), currency)
    count = len(balances)
    return (
        StatView("Total balance", format_money(total), "All accounts together",
                 "outflow" if total.is_negative() else "neutral"),
        StatView("What you have", format_money(assets), "Accounts in credit"),
        StatView("What you owe", format_money(owed),
                 "Nothing owed" if owed.is_zero() else "Accounts below zero (e.g. cards)"),
        StatView("Accounts", str(count), "Transfers move money between them"),
    )
