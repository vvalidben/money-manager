"""Statistics charts: category share donut, category changes, spending trend."""

from collections.abc import Sequence
from datetime import date

from matplotlib.lines import Line2D

from money_manager.domain.analytics import (
    CategoryAmount,
    CategoryChange,
    Granularity,
    SpendingTrend,
)
from money_manager.domain.money import sum_money
from money_manager.domain.health import ratio
from money_manager.ui.charts.base import (
    CATEGORICAL,
    EXPENSE_COLOR,
    GRID_COLOR,
    INCOME_COLOR,
    INK_MUTED,
    INK_SECONDARY,
    OTHER_COLOR,
    PREVIOUS_COLOR,
    SURFACE,
    ChartCanvas,
    TableData,
    money_axis,
    plot_value,
)
from money_manager.ui.formatting import (
    format_date,
    format_day_range,
    format_money,
    format_percent,
    format_signed_money,
    month_abbreviation,
)
from money_manager.core.i18n import tr

DONUT_SLICES = len(CATEGORICAL)  # top 5 get a colour; the rest fold into "Other"
CHANGE_ROWS = 8
MAX_TREND_TICKS = 6


def fold_categories(rows: Sequence[CategoryAmount]) -> list[CategoryAmount]:
    """Top categories plus one "Other" row, so the donut never needs a 6th hue."""
    if len(rows) <= DONUT_SLICES:
        return list(rows)
    rest = rows[DONUT_SLICES:]
    other = sum_money((row.amount for row in rest), rows[0].amount.currency)
    total = sum_money((row.amount for row in rows), rows[0].amount.currency)
    return [*rows[:DONUT_SLICES], CategoryAmount(None, tr("Other"), other, ratio(other, total))]


def category_colours(rows: Sequence[CategoryAmount], all_category_ids: Sequence[int]) -> list[str]:
    """Colours follow the category, not its size or the chosen range.

    Each category prefers the slot given by its position among *all*
    categories, so it keeps its colour when the range changes; only when two
    shown categories want the same slot does the later one take the next free
    slot. "Other" is always the neutral grey.
    """
    order = {category_id: index for index, category_id in enumerate(sorted(all_category_ids))}
    taken: dict[int, str] = {}
    free = list(CATEGORICAL)
    named = sorted(
        (row.category_id for row in rows if row.category_id is not None),
        key=lambda category_id: order.get(category_id, category_id),
    )
    for category_id in named:
        preferred = CATEGORICAL[order.get(category_id, category_id) % len(CATEGORICAL)]
        colour = preferred if preferred in free else free[0]
        free.remove(colour)
        taken[category_id] = colour
    return [OTHER_COLOR if row.category_id is None else taken[row.category_id] for row in rows]


class CategoryShareChart(ChartCanvas):
    """Donut of amounts per category (≤ 6 slices) with a labelled legend."""

    def __init__(self, height_px: int = 240, *, center_label: str = "spent") -> None:
        super().__init__(height_px)
        self._center_label = center_label

    def render(self, rows: Sequence[CategoryAmount], all_category_ids: Sequence[int]) -> None:
        slices = fold_categories(rows)
        if not slices:
            self.show_message(tr("No spending in this period"))
            return
        self.reset()
        ax = self.axes
        ax.grid(False)
        ax.spines["bottom"].set_visible(False)
        ax.set_xticks([])
        ax.set_yticks([])
        colours = category_colours(slices, all_category_ids)
        self.slice_colours = dict(zip((row.name for row in slices), colours, strict=True))
        wedges, _texts = ax.pie(
            [plot_value(row.amount) for row in slices],
            colors=colours,
            startangle=90,
            counterclock=False,
            wedgeprops={"width": 0.34, "edgecolor": SURFACE, "linewidth": 2},
        )
        total = sum_money((row.amount for row in slices), slices[0].amount.currency)
        total_text = format_money(total)
        ax.text(0, 0.08, total_text, ha="center", va="center",
                fontsize=10 if len(total_text) <= 12 else 8, fontweight="semibold",
                color=INK_SECONDARY)
        ax.text(0, -0.14, self._center_label, ha="center", va="center", color=INK_MUTED)
        labels = []
        for wedge, row in zip(wedges, slices, strict=True):
            share = "—" if row.share is None else format_percent(row.share)
            labels.append(f"{row.name}  {share}")
            self.add_hover(wedge, f"{row.name}\n{format_money(row.amount)} · {share}")
        ax.legend(wedges, labels, loc="center left", bbox_to_anchor=(1.0, 0.5), frameon=False,
                  handlelength=1, handleheight=1)
        ax.set_aspect("equal")
        self.draw_idle()


class CategoryChangeChart(ChartCanvas):
    """Dumbbell: each category's spending in the previous vs the current period."""

    def render(self, rows: Sequence[CategoryChange]) -> None:
        rows = list(rows[:CHANGE_ROWS])
        if not rows:
            self.show_message(tr("No spending in this or the previous period"))
            return
        self.reset()
        ax = self.axes
        ax.grid(axis="y", visible=False)
        ax.grid(axis="x", color=GRID_COLOR, linewidth=1, linestyle="-")
        ax.spines["bottom"].set_visible(False)
        positions = [len(rows) - 1 - index for index in range(len(rows))]  # biggest change on top
        largest = max(max(plot_value(r.previous), plot_value(r.current)) for r in rows)
        for position, row in zip(positions, rows, strict=True):
            before, after = plot_value(row.previous), plot_value(row.current)
            ax.plot([before, after], [position, position], color=GRID_COLOR, linewidth=2,
                    solid_capstyle="round", zorder=1)
            previous_dot = ax.scatter([before], [position], s=64, color=PREVIOUS_COLOR,
                                      edgecolors=SURFACE, linewidths=2, zorder=2)
            current_dot = ax.scatter([after], [position], s=64, color=INCOME_COLOR,
                                     edgecolors=SURFACE, linewidths=2, zorder=3)
            label = change_label(row)
            ax.text(largest * 1.04, position, label, va="center", ha="left", color=INK_SECONDARY)
            self.add_hover(previous_dot, tr("{0}\nPrevious: {1}", row.name, format_money(row.previous)))
            self.add_hover(current_dot, tr("{0}\nThis period: {1}\n{2}", row.name, format_money(row.current), label))
        ax.set_yticks(positions)
        ax.set_yticklabels([row.name for row in rows])
        ax.set_ylim(-0.7, len(rows) - 0.3)
        ax.set_xlim(0, largest * 1.3)
        money_axis(ax.xaxis)
        ax.legend(
            handles=[
                Line2D([], [], marker="o", linestyle="", markersize=8, color=PREVIOUS_COLOR,
                       label=tr("Previous period")),
                Line2D([], [], marker="o", linestyle="", markersize=8, color=INCOME_COLOR,
                       label=tr("This period")),
            ],
            loc="lower left", bbox_to_anchor=(0, 1.0), frameon=False, ncols=2,
            borderaxespad=0.2,
        )
        self.draw_idle()


def change_label(row: CategoryChange) -> str:
    if row.is_new:
        return "new"
    if row.change_ratio is None:
        return "—"
    return format_percent(row.change_ratio, signed=True)


class SpendingTrendChart(ChartCanvas):
    """Spending per day, week or month across the range (investments excluded)."""

    def render(self, trend: SpendingTrend) -> None:
        if not any(bucket.spending.is_positive() for bucket in trend.buckets):
            self.show_message(tr("No spending in this period"))
            return
        self.reset()
        ax = self.axes
        count = len(trend.buckets)
        width = 0.6 if count <= 12 else 0.8
        for index, bucket in enumerate(trend.buckets):
            [bar] = ax.bar(index, plot_value(bucket.spending), width=width, color=EXPENSE_COLOR)
            self.add_hover(bar, f"{bucket_label(trend.granularity, bucket.period.start, bucket.period.end)}"
                                f"\n{format_money(bucket.spending)}")
        step = max(1, -(-count // MAX_TREND_TICKS))  # ceiling division
        ticks = list(range(0, count, step))
        ax.set_xticks(ticks)
        ax.set_xticklabels([tick_label(trend.granularity, trend.buckets[i].period.start)
                            for i in ticks])
        ax.set_xlim(-0.6, count - 0.4)
        money_axis(ax.yaxis)
        self.draw_idle()


def tick_label(granularity: Granularity, start: date) -> str:
    if granularity is Granularity.MONTH:
        return month_abbreviation(start)
    return f"{start.day} {month_abbreviation(start)}"


def bucket_label(granularity: Granularity, start: date, end: date) -> str:
    if granularity is Granularity.DAY:
        return format_date(start)
    return format_day_range(start, end)


# ---------------------------------------------------------------- table twins


def category_share_table(rows: Sequence[CategoryAmount]) -> TableData:
    return (
        [tr("Category"), tr("Spent"), tr("Share")],
        [[r.name, format_money(r.amount), "—" if r.share is None else format_percent(r.share)]
         for r in rows],
    )


def category_change_table(rows: Sequence[CategoryChange]) -> TableData:
    return (
        [tr("Category"), tr("Previous"), tr("This period"), tr("Change"), "%"],
        [[r.name, format_money(r.previous), format_money(r.current),
          format_signed_money(r.change), change_label(r)] for r in rows],
    )


def spending_trend_table(trend: SpendingTrend) -> TableData:
    return (
        [tr("Period"), tr("Spending")],
        [[bucket_label(trend.granularity, b.period.start, b.period.end), format_money(b.spending)]
         for b in trend.buckets],
    )

