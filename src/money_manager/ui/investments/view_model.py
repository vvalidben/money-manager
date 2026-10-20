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
from money_manager.core.i18n import tr

KIND_TEXT = {
    InvestmentKind.STOCK: tr("Stock"),
    InvestmentKind.ETF: "ETF",
    InvestmentKind.CRYPTO: tr("Crypto"),
    InvestmentKind.GOLD: tr("Gold"),
    InvestmentKind.OTHER: tr("Other"),
}
# Stable ids so each type keeps its colour in the donut.
KIND_IDS = {kind: index for index, kind in enumerate(InvestmentKind, start=1)}

HOLDING_HEADERS = (tr("Name"), tr("Type"), tr("Net invested"), tr("Current value"), tr("Profit / loss"), tr("Return"),
                   tr("Last valued"))
ENTRY_HEADERS = (tr("Date"), tr("Type"), tr("Source"), tr("Note"), tr("Amount"))
VALUE_HEADERS = (tr("Date"), tr("Value"), tr("Note"))


def holding_row(position: InvestmentPosition) -> tuple[str, ...]:
    latest = position.latest_valuation
    value = position.current_value
    if value is None:
        value_text = tr("Not valued yet")
    else:
        value_text = format_money(value) + ("" if position.is_value_current else tr(" (out of date)"))
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
    source = (tr("External (not from your accounts)") if entry.transaction_id is None
              else tr("Paid from your accounts"))
    return (
        format_date(entry.occurred_on),
        tr("Contribution") if entry.kind is EntryKind.CONTRIBUTION else tr("Withdrawal"),
        source,
        entry.note,
        format_signed_money(entry.signed_amount),
    )


def value_row(valuation: Valuation) -> tuple[str, ...]:
    return (format_date(valuation.valued_on), format_money(valuation.value), valuation.note)


def position_status(position: InvestmentPosition) -> str:
    """Why a return is or is not shown."""
    if position.current_value is None:
        return tr("Enter the current value to see the profit or loss.")
    if not position.is_value_current:
        return (tr("Money moved in or out after the last value — update the value to see the "
                "current return."))
    if position.return_ratio is None:
        return tr("No return percentage: nothing is currently invested (withdrawals ≥ contributions).")
    return tr("Return calculated from your latest value.")


def summary_stats(summary: PortfolioSummary) -> tuple[StatView, ...]:
    count = len(summary.positions)
    profit, returns = summary.total_profit, summary.return_ratio
    if profit is None:
        profit_stat = StatView(tr("Profit / loss"), "—",
                               tr("Update the values of your investments to see returns"))
    else:
        caption = ("" if returns is None else f"{format_percent(returns, signed=True)} · ") + \
            tr("{0} of {1} up to date", len(summary.with_return), count)
        profit_stat = StatView(tr("Profit / loss"), format_signed_money(profit), caption,
                               "outflow" if profit.is_negative() else "inflow")
    return (
        StatView(tr("Portfolio value"), format_money(summary.total_value),
                 tr("{0} of {1} investments valued", len(summary.valued), count)),
        StatView(tr("Net invested"), format_money(summary.net_invested),
                 tr("Contributed {0} · withdrawn {1}", format_money(summary.contributed), format_money(summary.withdrawn))),
        profit_stat,
        StatView(tr("Net worth"), format_money(summary.net_worth),
                 tr("Balance {0} + investments", format_money(summary.total_balance))),
    )


def value_by_kind(summary: PortfolioSummary) -> list[CategoryAmount]:
    """Current value per type, shaped for the shared share donut."""
    return [CategoryAmount(KIND_IDS[row.kind], KIND_TEXT[row.kind], row.value, row.share)
            for row in summary.by_kind]
