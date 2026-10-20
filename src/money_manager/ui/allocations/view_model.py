"""Turns the allocation summary into display text (pure presentation, no Qt).

Every amount comes from ``AllocationService``; this module only words it.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

from money_manager.domain.allocation import AllocationSummary
from money_manager.domain.entities import AllocationTransfer
from money_manager.domain.health import ratio
from money_manager.ui.dashboard.view_model import StatView
from money_manager.ui.formatting import format_date, format_money, format_percent
from money_manager.core.i18n import tr

AVAILABLE = tr("Available")


@dataclass(frozen=True, slots=True)
class AllocationCardView:
    allocation_id: int
    name: str
    balance: str
    share_fraction: Decimal  # of the total balance, 0…1 (drawing only)
    share: str
    goal: str  # "Backs the goal Car", or ""
    can_archive: bool  # goal-backed allocations are managed from the goal


@dataclass(frozen=True, slots=True)
class MoveView:
    transfer_id: int
    date: str
    route: str
    amount: str
    note: str


def allocation_cards(summary: AllocationSummary,
                     goal_names: Mapping[int, str]) -> tuple[AllocationCardView, ...]:
    """Active allocations, largest first."""
    total = summary.total_balance
    cards = []
    rows = sorted((r for r in summary.allocations if not r.allocation.is_archived),
                  key=lambda r: (-r.balance.amount, r.allocation.name.casefold()))
    for row in rows:
        share = ratio(row.balance, total) if total.is_positive() else None
        goal = goal_names.get(row.allocation.id)
        cards.append(AllocationCardView(
            allocation_id=row.allocation.id,
            name=row.allocation.name,
            balance=format_money(row.balance),
            share_fraction=min(max(share or Decimal(0), Decimal(0)), Decimal(1)),
            share="—" if share is None else tr("{0} of your total balance", format_percent(share)),
            goal=tr("Backs the goal {0}", goal) if goal else "",
            can_archive=goal is None,
        ))
    return tuple(cards)


def summary_stats(summary: AllocationSummary) -> tuple[StatView, ...]:
    available, total = summary.available, summary.total_balance
    count = sum(1 for r in summary.allocations if not r.allocation.is_archived)
    return (
        StatView(tr("Available"), format_money(available),
                 tr("Not set aside for anything") if not available.is_negative()
                 else tr("More is set aside than you have"),
                 "outflow" if available.is_negative() else "neutral"),
        StatView(tr("Total balance"), format_money(total), tr("All accounts together"),
                 "outflow" if total.is_negative() else "neutral"),
        StatView(tr("Set aside"), format_money(summary.allocated_total),
                 tr("In {0} allocation{1}", count, '' if count == 1 else 's')),
        StatView(tr("Allocations"), str(count), tr("Goals keep their money in one")),
    )


def over_allocation_note(summary: AllocationSummary) -> str:
    if not summary.is_over_allocated:
        return ""
    return (tr("More is set aside than you have: Available is short by {0}. Take money "
               "out of an allocation to fix it.", format_money(summary.shortfall)))


def move_views(transfers: Sequence[AllocationTransfer], names: Mapping[int, str],
               limit: int = 8) -> tuple[MoveView, ...]:
    """The most recent moves, newest first."""
    def name(allocation_id: int | None) -> str:
        return AVAILABLE if allocation_id is None else names.get(allocation_id, "?")

    return tuple(
        MoveView(transfer.id, format_date(transfer.occurred_on),
                 f"{name(transfer.from_allocation_id)} → {name(transfer.to_allocation_id)}",
                 format_money(transfer.amount), transfer.note)
        for transfer in transfers[:limit]
    )
