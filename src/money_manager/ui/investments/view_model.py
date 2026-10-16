"""Display text for investments (pure presentation, no Qt, no calculations)."""

from money_manager.domain.analytics import CategoryAmount
from money_manager.domain.investments import (
    EntryKind,
    InvestmentEntry,
    InvestmentKind,
    InvestmentPosition,
    PortfolioSummary,
    Valuation,
)
from money_manager.ui.dashboard.view_model import StatView
from money_manager.ui.formatting import (
    format_date,
    format_money,
    format_percent,
    format_signed_money,
)

KIND_TEXT = {
    InvestmentKind.STOCK: "Stock",
    InvestmentKind.ETF: "ETF",
    InvestmentKind.CRYPTO: "Crypto",
    InvestmentKind.GOLD: "Gold",
    InvestmentKind.OTHER: "Other",
}
# Stable ids so each type keeps its colour in the donut.
KIND_IDS = {kind: index for index, kind in enumerate(InvestmentKind, start=1)}

HOLDING_HEADERS = ("Name", "Type", "Net invested", "Current value", "Profit / loss", "Return",
                   "Last valued")
ENTRY_HEADERS = ("Date", "Type", "Source", "Note", "Amount")
VALUE_HEADERS = ("Date", "Value", "Note")


def holding_row(position: InvestmentPosition) -> tuple[str, ...]:
    latest = position.latest_valuation
    value = position.current_value
    if value is None:
        value_text = "Not valued yet"
    else:
        value_text = format_money(value) + ("" if position.is_value_current else " (out of date)")
    profit = position.profit
    returns = position.return_ratio
    return (
        position.investment.name,
        KIND_TEXT[position.investment.kind],
        format_money(position.net_invested),
        value_text,
        "—" if profit is None else format_signed_money(profit),
        "—" if returns is None else format_percent(returns, signed=True),
        "—" if latest is None else format_date(latest.valued_on),
    )


def entry_row(entry: InvestmentEntry) -> tuple[str, ...]:
    source = ("External (not from your accounts)" if entry.transaction_id is None
              else "Paid from your accounts")
    return (
        format_date(entry.occurred_on),
        "Contribution" if entry.kind is EntryKind.CONTRIBUTION else "Withdrawal",
        source,
        entry.note,
        format_signed_money(entry.signed_amount),
    )


def value_row(valuation: Valuation) -> tuple[str, ...]:
    return (format_date(valuation.valued_on), format_money(valuation.value), valuation.note)


def position_status(position: InvestmentPosition) -> str:
    """Why a return is or is not shown."""
    if position.current_value is None:
        return "Enter the current value to see the profit or loss."
    if not position.is_value_current:
        return ("Money moved in or out after the last value — update the value to see the "
                "current return.")
    if position.return_ratio is None:
        return "No return percentage: nothing is currently invested (withdrawals ≥ contributions)."
    return "Return calculated from your latest value."


def summary_stats(summary: PortfolioSummary) -> tuple[StatView, ...]:
    count = len(summary.positions)
    profit, returns = summary.total_profit, summary.return_ratio
    if profit is None:
        profit_stat = StatView("Profit / loss", "—",
                               "Update the values of your investments to see returns")
    else:
        caption = ("" if returns is None else f"{format_percent(returns, signed=True)} · ") + \
            f"{len(summary.with_return)} of {count} up to date"
        profit_stat = StatView("Profit / loss", format_signed_money(profit), caption,
                               "outflow" if profit.is_negative() else "inflow")
    return (
        StatView("Portfolio value", format_money(summary.total_value),
                 f"{len(summary.valued)} of {count} investments valued"),
        StatView("Net invested", format_money(summary.net_invested),
                 f"Contributed {format_money(summary.contributed)} · "
                 f"withdrawn {format_money(summary.withdrawn)}"),
        profit_stat,
        StatView("Net worth", format_money(summary.net_worth),
                 f"Balance {format_money(summary.total_balance)} + investments"),
    )


def value_by_kind(summary: PortfolioSummary) -> list[CategoryAmount]:
    """Current value per type, shaped for the shared share donut."""
    return [CategoryAmount(KIND_IDS[row.kind], KIND_TEXT[row.kind], row.value, row.share)
            for row in summary.by_kind]
