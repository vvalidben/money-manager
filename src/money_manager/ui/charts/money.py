"""Money-flow charts shared by the dashboard and the statistics page."""

from bisect import bisect_left
from collections.abc import Sequence

from matplotlib.backend_bases import MouseEvent
from matplotlib.dates import AutoDateLocator, ConciseDateFormatter, date2num

from money_manager.domain.analytics import BalancePoint
from money_manager.domain.dashboard import CategorySpending, MonthlyFlow
from money_manager.domain.investments import NetWorthPoint
from money_manager.ui.charts.base import (
    AXIS_COLOR,
    BALANCE_COLOR,
    CATEGORICAL,
    EXPENSE_COLOR,
    GRID_COLOR,
    INCOME_COLOR,
    INK_SECONDARY,
    SURFACE,
    ChartCanvas,
    TableData,
    money_axis,
    plot_value,
)
from money_manager.ui.formatting import (
    format_date,
    format_money,
    format_month,
    format_percent,
    month_abbreviation,
)

CATEGORY_SLOTS = 6  # top 5 + Other
DAILY_TABLE_MAX_POINTS = 31


class IncomeExpenseChart(ChartCanvas):
    """Grouped columns: income vs expenses for each month."""

    def render(self, flows: Sequence[MonthlyFlow], *, last_is_partial: bool = True) -> None:
        if not any(f.income.is_positive() or f.expenses.is_positive() for f in flows):
            self.show_message("No income or expenses recorded in the last months")
            return
        self.reset()
        ax = self.axes
        width, gap = 0.34, 0.03  # bar width in month units, with a small surface gap
        for index, flow in enumerate(flows):
            label = format_month(flow.month)
            for offset, value, color, kind in (
                (-(width + gap) / 2, flow.income, INCOME_COLOR, "Income"),
                ((width + gap) / 2, flow.expenses, EXPENSE_COLOR, "Expenses"),
            ):
                [bar] = ax.bar(index + offset, plot_value(value), width=width, color=color,
                               label=kind if index == 0 else None)
                self.add_hover(bar, f"{label}\n{kind}: {format_money(value)}")
        ax.set_xticks(range(len(flows)))
        ax.set_xticklabels(
            [month_abbreviation(f.month)
             + ("\n(to date)" if last_is_partial and i == len(flows) - 1 else "")
             for i, f in enumerate(flows)]
        )
        tallest = max(max(plot_value(f.income), plot_value(f.expenses)) for f in flows)
        ax.set_ylim(0, tallest * 1.1)  # headroom so bars never touch the frame
        money_axis(ax.yaxis)
        # Legend above the plot area so it can never cover a bar.
        ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), frameon=False, ncols=2,
                  handlelength=1, handleheight=1, borderaxespad=0.2)
        self.draw_idle()


class BalanceHistoryChart(ChartCanvas):
    """Single series: total balance at the end of each day."""

    def __init__(self, height_px: int = 240) -> None:
        super().__init__(height_px)
        self._points: list[BalancePoint] = []
        self._xs: list[float] = []

    def render(self, points: Sequence[BalancePoint]) -> None:
        self._points, self._xs = [], []
        if len(points) < 2:
            self.show_message("The balance history appears after your first days of tracking")
            return
        self.reset()
        ax = self.axes
        xs = [date2num(point.day) for point in points]
        ys = [plot_value(point.balance) for point in points]
        ax.plot(xs, ys, color=BALANCE_COLOR, linewidth=2, solid_joinstyle="round",
                solid_capstyle="round", drawstyle="steps-post")
        ax.fill_between(xs, ys, 0, step="post", color=BALANCE_COLOR, alpha=0.10, linewidth=0)
        if min(ys) < 0 < max(ys):
            ax.axhline(0, color=AXIS_COLOR, linewidth=1)
        last = points[-1]
        ax.plot([xs[-1]], [ys[-1]], marker="o", markersize=8, color=BALANCE_COLOR,
                markeredgecolor=SURFACE, markeredgewidth=2, zorder=3)
        ax.annotate(format_money(last.balance), (xs[-1], ys[-1]), xytext=(-8, 10),
                    textcoords="offset points", ha="right", color=INK_SECONDARY, zorder=4,
                    bbox={"boxstyle": "round,pad=0.25", "facecolor": SURFACE, "edgecolor": "none"})
        locator = AutoDateLocator(minticks=3, maxticks=7)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(ConciseDateFormatter(locator, show_offset=False))
        money_axis(ax.yaxis)
        span = xs[-1] - xs[0]
        ax.set_xlim(xs[0], xs[-1] + span * 0.02)  # keep the end marker inside the frame
        self._points = list(points)
        self._xs = xs
        self.draw_idle()

    def hover_text(self, event: MouseEvent) -> str | None:
        """Anywhere over the plot: the balance of the nearest day."""
        if event.inaxes is not self.axes or event.xdata is None or not self._points:
            return None
        index = min(bisect_left(self._xs, event.xdata), len(self._xs) - 1)
        if index > 0 and event.xdata - self._xs[index - 1] < self._xs[index] - event.xdata:
            index -= 1
        point = self._points[index]
        return f"{format_date(point.day)}\n{format_money(point.balance)}"


INVESTMENTS_COLOR = CATEGORICAL[1]  # violet next to the lime net-worth line


class NetWorthChart(ChartCanvas):
    """Net worth at each month end; with investments, the balance line below it and
    the band between them is what the investments add."""

    def __init__(self, height_px: int = 240) -> None:
        super().__init__(height_px)
        self._points: list[NetWorthPoint] = []

    def render(self, points: Sequence[NetWorthPoint]) -> None:
        self._points = []
        if len(points) < 2:
            self.show_message("Your net worth over time appears after your first month")
            return
        self.reset()
        ax = self.axes
        xs = list(range(len(points)))
        worth = [plot_value(p.net_worth) for p in points]
        has_investments = any(not p.investments.is_zero() for p in points)
        if has_investments:
            balance = [plot_value(p.balance) for p in points]
            ax.fill_between(xs, balance, worth, color=INVESTMENTS_COLOR, alpha=0.28, linewidth=0,
                            label="Investments")
            ax.plot(xs, balance, color=INVESTMENTS_COLOR, linewidth=1.5, label="Balance")
        ax.plot(xs, worth, color=BALANCE_COLOR, linewidth=2, marker="o", markersize=4,
                solid_joinstyle="round", solid_capstyle="round", label="Net worth")
        if min(worth) < 0 < max(worth):
            ax.axhline(0, color=AXIS_COLOR, linewidth=1)
        ax.plot([xs[-1]], [worth[-1]], marker="o", markersize=8, color=BALANCE_COLOR,
                markeredgecolor=SURFACE, markeredgewidth=2, zorder=3)
        ax.annotate(format_money(points[-1].net_worth), (xs[-1], worth[-1]), xytext=(-8, 10),
                    textcoords="offset points", ha="right", color=INK_SECONDARY, zorder=4,
                    bbox={"boxstyle": "round,pad=0.25", "facecolor": SURFACE, "edgecolor": "none"})
        ax.set_xticks(xs)
        ax.set_xticklabels([month_abbreviation(p.month) for p in points])
        ax.set_xlim(-0.3, xs[-1] + 0.3)
        money_axis(ax.yaxis)
        if has_investments:
            ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), frameon=False, ncols=3,
                      handlelength=1.4, borderaxespad=0.2)
        self._points = list(points)
        self.draw_idle()

    def hover_text(self, event: MouseEvent) -> str | None:
        """Anywhere over the plot: the nearest month's figures."""
        if event.inaxes is not self.axes or event.xdata is None or not self._points:
            return None
        return net_worth_text(self._points[min(max(round(event.xdata), 0),
                                                len(self._points) - 1)])


def net_worth_text(point: NetWorthPoint) -> str:
    return (f"{format_month(point.month)} · {format_date(point.on)}\n"
            f"Net worth: {format_money(point.net_worth)}\n"
            f"Balance: {format_money(point.balance)}\n"
            f"Investments: {format_money(point.investments)}")


class CategorySpendingChart(ChartCanvas):
    """Horizontal bars, largest first; one series, one colour, value at the tip."""

    def render(self, rows: Sequence[CategorySpending]) -> None:
        if not rows:
            self.show_message("No expenses recorded this month")
            return
        self.reset()
        ax = self.axes
        ax.grid(axis="y", visible=False)
        ax.grid(axis="x", color=GRID_COLOR, linewidth=1, linestyle="-")
        ax.spines["bottom"].set_visible(False)
        # A fixed number of slots keeps bars thin (≈20px) even with few categories;
        # rows fill the slots from the top, largest first.
        slots = max(len(rows), CATEGORY_SLOTS)
        positions = [slots - 1 - index for index in range(len(rows))]
        ax.set_ylim(-0.5, slots - 0.5)
        largest = max(plot_value(row.amount) for row in rows)
        for position, row in zip(positions, rows, strict=True):
            [bar] = ax.barh(position, plot_value(row.amount), height=0.55, color=EXPENSE_COLOR)
            share = "" if row.share is None else f" · {format_percent(row.share)}"
            ax.text(plot_value(row.amount) + largest * 0.02, position, f"{format_money(row.amount)}{share}",
                    va="center", ha="left", color=INK_SECONDARY)
            self.add_hover(bar, f"{row.name}\n{format_money(row.amount)}{share}")
        ax.set_yticks(positions)
        ax.set_yticklabels([row.name for row in rows])
        ax.set_xlim(0, largest * 1.55)  # room for the labels at the bar tips
        ax.set_xticks([])
        self.draw_idle()


# ---------------------------------------------------------------- table twins


def income_expense_table(flows: Sequence[MonthlyFlow]) -> TableData:
    return (
        ["Month", "Income", "Expenses", "Net"],
        [[format_month(f.month), format_money(f.income), format_money(f.expenses),
          format_money(f.net)] for f in flows],
    )


def balance_history_table(points: Sequence[BalancePoint]) -> TableData:
    """Every day for short ranges; month ends (and the last day) for longer ones."""
    if len(points) <= DAILY_TABLE_MAX_POINTS:
        return ["Date", "Balance"], [[format_date(p.day), format_money(p.balance)] for p in points]
    rows = [
        [format_date(p.day), format_money(p.balance)]
        for index, p in enumerate(points)
        if index == len(points) - 1 or points[index + 1].day.month != p.day.month
    ]
    return ["Date", "Balance"], rows


def net_worth_table(points: Sequence[NetWorthPoint]) -> TableData:
    return (
        ["Month", "Balance", "Investments", "Net worth"],
        [[format_month(p.month), format_money(p.balance), format_money(p.investments),
          format_money(p.net_worth)] for p in points],
    )


def category_spending_table(rows: Sequence[CategorySpending]) -> TableData:
    return (
        ["Category", "Spent", "Share"],
        [[r.name, format_money(r.amount), "—" if r.share is None else format_percent(r.share)]
         for r in rows],
    )
