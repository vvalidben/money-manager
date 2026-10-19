"""The monthly report as a printable PDF (A4, light colours, no network).

The page is HTML laid out by ``QTextDocument`` and printed by ``QPdfWriter``;
the two charts are Matplotlib figures embedded as images. Every figure shown as
text is formatted from the exact ``Money`` values; floats only place marks.
Names and descriptions typed by the user are escaped.
"""

from collections.abc import Sequence
from decimal import Decimal
from html import escape
from io import BytesIO
from pathlib import Path

from matplotlib.figure import Figure
from PySide6.QtCore import QMarginsF, QSizeF, QUrl
from PySide6.QtGui import QFont, QImage, QPageLayout, QPageSize, QPdfWriter, QTextDocument

from money_manager import __version__
from money_manager.domain.analytics import CategoryAmount
from money_manager.domain.investments import NetWorthPoint
from money_manager.domain.money import sum_money
from money_manager.domain.report import MonthlyReport
from money_manager.ui.charts.base import plot_value
from money_manager.ui.formatting import (
    format_compact_amount,
    format_date,
    format_day_range,
    format_money,
    format_month,
    format_percent,
    format_signed_money,
    month_abbreviation,
)
from money_manager.ui.theme import FONT_FAMILY

# Print palette: dark ink on white; the series colours are the app's validated
# chart colours, which also read on paper.
INK = "#16181d"
MUTED = "#5f6470"
RULE = "#d9dce3"
HEAD_BG = "#f1f2f5"
GOOD = "#2f7d32"
BAD = "#b3401a"
LINE = "#5f7d1c"  # a darker step of the lime accent, for paper
BAND = "#9085e9"
BAR = "#3987e5"
CHART_SLOTS = 7
MARGINS_MM = QMarginsF(16, 14, 16, 14)
A4_MM = (210, 297)
LAYOUT_DPI = 96  # the document is laid out in 96-dpi pixels, then scaled to the page
TEXT_WIDTH_PX = round((A4_MM[0] - MARGINS_MM.left() - MARGINS_MM.right()) / 25.4 * LAYOUT_DPI)
CHART_WIDTH_PX = TEXT_WIDTH_PX  # images are rendered at 3x for print

NET_WORTH_URL = "chart://net-worth"
SPENDING_URL = "chart://spending"


def write_monthly_report(report: MonthlyReport, path: Path) -> None:
    """Write the report to ``path`` (overwritten)."""
    document = build_document(report)
    writer = QPdfWriter(str(path))
    writer.setTitle(f"Money Manager — {format_month(report.month)}")
    writer.setCreator(f"Money Manager {__version__}")
    writer.setResolution(300)
    writer.setPageLayout(QPageLayout(QPageSize(QPageSize.PageSizeId.A4),
                                     QPageLayout.Orientation.Portrait,
                                     MARGINS_MM, QPageLayout.Unit.Millimeter))
    document.print_(writer)
    if not path.is_file() or path.stat().st_size == 0:
        raise OSError(f"The report could not be written to {path}.")


def build_document(report: MonthlyReport) -> QTextDocument:
    document = QTextDocument()
    document.setDefaultFont(QFont(FONT_FAMILY, 10))
    document.setDocumentMargin(0)
    # A page size of its own keeps Qt from adding a second margin when printing.
    text_height_mm = A4_MM[1] - MARGINS_MM.top() - MARGINS_MM.bottom()
    document.setPageSize(QSizeF(TEXT_WIDTH_PX, text_height_mm / 25.4 * LAYOUT_DPI))
    images = {SPENDING_URL: spending_chart(report.statistics.spending_by_category)}
    if len(report.net_worth) >= 2:
        images[NET_WORTH_URL] = net_worth_chart(report.net_worth)
    for url, image in images.items():
        document.addResource(QTextDocument.ResourceType.ImageResource, QUrl(url), image)
    document.setHtml(report_html(report, charts=set(images)))
    return document


# ---------------------------------------------------------------------- HTML

def report_html(report: MonthlyReport, *, charts: set[str] | None = None) -> str:
    charts = set() if charts is None else charts
    parts = [_STYLE, _title(report), _summary(report), _net_worth(report, NET_WORTH_URL in charts),
             _budgets(report), _goals(report), _spending(report, SPENDING_URL in charts),
             _largest(report), _footer(report)]
    return "<html><body>" + "".join(parts) + "</body></html>"


_STYLE = f"""<style>
body {{ color: {INK}; }}
h1 {{ font-size: 20pt; font-weight: 600; margin: 0; }}
h2 {{ font-size: 12.5pt; font-weight: 600; margin-top: 18px; margin-bottom: 6px; }}
p {{ margin: 0; }}
.muted {{ color: {MUTED}; }}
.small {{ font-size: 8.5pt; }}
.kpi {{ font-size: 13pt; font-weight: 600; white-space: nowrap; }}
.good {{ color: {GOOD}; }}
.bad {{ color: {BAD}; }}
table.data {{ border-collapse: collapse; }}
table.data th {{ background-color: {HEAD_BG}; color: {MUTED}; font-weight: 600;
                 font-size: 8.5pt; text-align: left; }}
table.data td {{ border-bottom: 1px solid {RULE}; }}
</style>"""


def _title(report: MonthlyReport) -> str:
    span = format_day_range(report.period.start, report.period.end)
    scope = span if report.is_complete else f"{span}, month to date"
    return (f"<p class='muted small'>MONEY MANAGER · MONTHLY REPORT</p>"
            f"<h1>{format_month(report.month)}</h1>"
            f"<p class='muted'>{scope} · made on {format_date(report.generated_on)}</p>")


def _summary(report: MonthlyReport) -> str:
    stats = report.statistics
    now, before = stats.totals, stats.previous_totals
    previous = previous_label(report) if stats.comparison_complete else None
    cells = []
    for label, value, prior, higher_is_good in (
        ("Income", now.income, before.income, True),
        ("Spending", now.spending, before.spending, False),
        ("Invested", now.investments, before.investments, True),
        ("Saved", now.savings, before.savings, True),
    ):
        change = ""
        if previous is not None:
            delta = value - prior
            tone = "" if delta.is_zero() else (
                "good" if delta.is_positive() == higher_is_good else "bad")
            change = (f"<br><span class='small {tone}'>{format_signed_money(delta)}"
                      f"</span><span class='small muted'> vs {previous}</span>")
        cells.append(f"<td width='25%'><p class='muted small'>{label.upper()}</p>"
                     f"<p class='kpi'>{format_money(value)}</p>{change}</td>")
    rate = now.savings_rate
    if rate is None:
        rate_text = "No income recorded, so there is no savings rate."
    elif now.savings.is_negative():
        rate_text = f"You spent <b>{format_money(-now.savings)}</b> more than your income."
    else:
        rate_text = (f"You kept <b>{format_percent(rate)}</b> of your income "
                     f"(income − spending; money invested counts as kept).")
    return ("<h2>Summary</h2><table width='100%' cellpadding='4' cellspacing='0'><tr>"
            + "".join(cells) + f"</tr></table><p class='muted small'>{rate_text}</p>")


def _net_worth(report: MonthlyReport, with_chart: bool) -> str:
    if not report.net_worth:
        return ""
    last = report.net_worth[-1]
    rows = [("Balance of your accounts", last.balance),
            ("Investments (latest values entered)", last.investments),
            ("<b>Net worth</b>", last.net_worth)]
    table = "".join(f"<tr><td>{label}</td><td align='right'>{format_money(value)}</td></tr>"
                    for label, value in rows)
    chart = (f"<p><img src='{NET_WORTH_URL}' width='{CHART_WIDTH_PX}'></p>" if with_chart else "")
    return (f"<h2>Balance and net worth on {format_date(last.on)}</h2>"
            f"<table class='data' width='60%' cellpadding='5'>{table}</table>{chart}")


def _spending(report: MonthlyReport, with_chart: bool) -> str:
    stats = report.statistics
    rows = stats.spending_by_category
    if not rows:
        return ("<h2 style='page-break-before: always'>Where the money went</h2>"
                "<p class='muted'>No spending recorded.</p>")
    changes = {c.category_id: c for c in stats.category_changes}
    body = []
    for row in rows:
        change = changes.get(row.category_id)
        delta = ("—" if change is None or not stats.comparison_complete
                 else format_signed_money(change.change))
        share = "—" if row.share is None else format_percent(row.share)
        body.append(f"<tr><td>{escape(row.name)}</td><td align='right'>{format_money(row.amount)}"
                    f"</td><td align='right'>{share}</td><td align='right'>{delta}</td></tr>")
    chart = f"<p><img src='{SPENDING_URL}' width='{CHART_WIDTH_PX}'></p>" if with_chart else ""
    return ("<h2 style='page-break-before: always'>Where the money went</h2>" + chart
            + "<table class='data' width='100%' cellpadding='5'><tr><th>Category</th>"
            "<th align='right'>Spent</th><th align='right'>Share</th>"
            f"<th align='right'>vs {previous_label(report)}</th></tr>" + "".join(body) + "</table>")


def previous_label(report: MonthlyReport) -> str:
    """``Aug 2026`` for a whole month, ``1–19 Sep`` for month to date."""
    previous = report.statistics.previous_period
    return (format_month(previous.start) if report.is_complete
            else format_day_range(previous.start, previous.end))


def _budgets(report: MonthlyReport) -> str:
    statuses = report.budgets.statuses
    if not statuses:
        return ""
    body = []
    for status in statuses:
        tone = {"over": "bad", "near_limit": "", "on_track": "good"}[status.level.value]
        body.append(
            f"<tr><td>{escape(status.category_name)}</td>"
            f"<td align='right'>{format_money(status.budget.limit)}</td>"
            f"<td align='right'>{format_money(status.spent)}</td>"
            f"<td align='right'>{format_money(status.remaining)}</td>"
            f"<td class='{tone}'>{status.level.label}</td></tr>")
    return ("<h2>Budgets</h2><table class='data' width='100%' cellpadding='5'><tr>"
            "<th>Category</th><th align='right'>Limit</th><th align='right'>Spent</th>"
            "<th align='right'>Left</th><th>Status</th></tr>" + "".join(body) + "</table>")


def _goals(report: MonthlyReport) -> str:
    if not report.goals:
        return ""
    body = []
    for goal in report.goals:
        deadline = "—" if goal.goal.deadline is None else format_date(goal.goal.deadline)
        body.append(
            f"<tr><td>{escape(goal.goal.name)}</td><td align='right'>{format_money(goal.saved)}</td>"
            f"<td align='right'>{format_money(goal.goal.target)}</td>"
            f"<td align='right'>{format_percent(goal.progress)}</td><td>{deadline}</td></tr>")
    return (f"<h2>Goals on {format_date(report.generated_on)}</h2>"
            "<table class='data' width='100%' cellpadding='5'><tr><th>Goal</th>"
            "<th align='right'>Saved</th><th align='right'>Target</th><th align='right'>Progress</th>"
            "<th>Deadline</th></tr>" + "".join(body) + "</table>")


def _largest(report: MonthlyReport) -> str:
    if not report.largest_expenses:
        return ""
    body = []
    for t in report.largest_expenses:
        category = report.category_names.get(t.category_id, "—") if t.category_id else "—"
        body.append(f"<tr><td>{format_date(t.occurred_on)}</td><td>{escape(t.description)}</td>"
                    f"<td>{escape(category)}</td><td align='right'>{format_money(t.amount)}</td></tr>")
    return ("<h2>Largest expenses</h2><table class='data' width='100%' cellpadding='5'><tr>"
            "<th>Date</th><th>Description</th><th>Category</th><th align='right'>Amount</th></tr>"
            + "".join(body) + "</table>")


def _footer(report: MonthlyReport) -> str:
    return (f"<p class='muted small' style='margin-top: 18px'>Made by Money Manager {__version__}"
            f" on your computer from the entries you recorded. Amounts in {report.currency}."
            " Transfers between your accounts and balance corrections are not counted as "
            "income or spending.</p>")


# -------------------------------------------------------------------- charts

def _figure(height_in: float) -> Figure:
    figure = Figure(figsize=(CHART_WIDTH_PX / 96, height_in), dpi=96 * 3, layout="constrained")
    figure.patch.set_facecolor("white")
    return figure


def _style_axes(ax) -> None:  # noqa: ANN001 - Matplotlib axes
    ax.set_facecolor("white")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(RULE)
    ax.tick_params(colors=MUTED, labelsize=8, length=0)
    ax.grid(axis="y", color="#eceef2", linewidth=0.8)
    ax.set_axisbelow(True)


def _image(figure: Figure) -> QImage:
    buffer = BytesIO()
    figure.savefig(buffer, format="png", facecolor="white")
    image = QImage()
    image.loadFromData(buffer.getvalue(), "PNG")
    return image


def net_worth_chart(points: Sequence[NetWorthPoint]) -> QImage:
    figure = _figure(2.3)
    ax = figure.add_subplot()
    _style_axes(ax)
    xs = list(range(len(points)))
    worth = [plot_value(p.net_worth) for p in points]
    if any(not p.investments.is_zero() for p in points):
        balance = [plot_value(p.balance) for p in points]
        ax.fill_between(xs, balance, worth, color=BAND, alpha=0.25, linewidth=0,
                        label="Investments")
        ax.plot(xs, balance, color=BAND, linewidth=1.4, label="Balance")
    ax.plot(xs, worth, color=LINE, linewidth=2, marker="o", markersize=3.5, label="Net worth")
    if any(not p.investments.is_zero() for p in points):
        ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), frameon=False, fontsize=8, ncols=3,
                  labelcolor=MUTED, borderaxespad=0.2)
    ax.set_xticks(xs, [month_abbreviation(p.month) for p in points])
    ax.yaxis.set_major_formatter(_compact)
    return _image(figure)


def spending_chart(rows: Sequence[CategoryAmount]) -> QImage:
    shown = list(rows[:CHART_SLOTS])
    rest = rows[CHART_SLOTS:]
    if rest:
        currency = rest[0].amount.currency
        shown[-1:] = [CategoryAmount(None, "Other", sum_money(
            (r.amount for r in [shown[-1], *rest]), currency), None)]
    figure = _figure(0.35 + 0.28 * max(len(shown), 1))
    ax = figure.add_subplot()
    _style_axes(ax)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color="#eceef2", linewidth=0.8)
    names = [r.name if len(r.name) <= 24 else r.name[:23] + "…" for r in shown][::-1]
    values = [plot_value(r.amount) for r in shown][::-1]
    bars = ax.barh(names, values, color=BAR, height=0.6)
    for bar, row in zip(bars, shown[::-1], strict=True):
        ax.annotate(format_money(row.amount), (bar.get_width(), bar.get_y() + bar.get_height() / 2),
                    xytext=(4, 0), textcoords="offset points", va="center", fontsize=7.5,
                    color=INK)
    ax.set_xlim(0, max(values, default=1) * 1.25 or 1)
    ax.xaxis.set_major_formatter(_compact)
    return _image(figure)


def _compact(value: float, _pos: int) -> str:
    return format_compact_amount(Decimal(str(round(value))))
