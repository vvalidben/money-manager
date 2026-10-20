"""The yearly report as a printable PDF (same look as the monthly report)."""

from html import escape
from pathlib import Path

from PySide6.QtCore import QSizeF, Qt, QUrl
from PySide6.QtGui import QFont, QImage, QPageLayout, QPageSize, QPdfWriter, QTextDocument

from money_manager import __version__
from money_manager.core.i18n import is_right_to_left, tr
from money_manager.domain.report import YearlyReport
from money_manager.ui.charts.base import plot_value
from money_manager.ui.formatting import (
    format_date,
    format_day_range,
    format_money,
    format_month,
    format_percent,
    format_signed_money,
    month_abbreviation,
)
from money_manager.ui.reports.monthly_pdf import (
    A4_MM,
    BAR,
    CHART_WIDTH_PX,
    LAYOUT_DPI,
    MARGINS_MM,
    MUTED,
    STYLE,
    TEXT_WIDTH_PX,
    _compact,
    _figure,
    _image,
    _style_axes,
    net_worth_chart,
    spending_chart,
)
from money_manager.ui.theme import FONT_FAMILY

SPEND = "#d95926"
MONTHS_URL = "chart://months"
NET_WORTH_URL = "chart://year-net-worth"
SPENDING_URL = "chart://year-spending"


def write_yearly_report(report: YearlyReport, path: Path) -> None:
    document = QTextDocument()
    document.setDefaultFont(QFont(FONT_FAMILY, 10))
    document.setDocumentMargin(0)
    if is_right_to_left():
        option = document.defaultTextOption()
        option.setTextDirection(Qt.LayoutDirection.RightToLeft)
        document.setDefaultTextOption(option)
    height_mm = A4_MM[1] - MARGINS_MM.top() - MARGINS_MM.bottom()
    document.setPageSize(QSizeF(TEXT_WIDTH_PX, height_mm / 25.4 * LAYOUT_DPI))
    images = {MONTHS_URL: months_chart(report),
              SPENDING_URL: spending_chart(report.statistics.spending_by_category)}
    if len(report.net_worth) >= 2:
        images[NET_WORTH_URL] = net_worth_chart(report.net_worth)
    for url, image in images.items():
        document.addResource(QTextDocument.ResourceType.ImageResource, QUrl(url), image)
    document.setHtml(report_html(report, charts=set(images)))
    writer = QPdfWriter(str(path))
    writer.setTitle(f"Money Manager — {report.year}")
    writer.setCreator(f"Money Manager {__version__}")
    writer.setResolution(300)
    writer.setPageLayout(QPageLayout(QPageSize(QPageSize.PageSizeId.A4),
                                     QPageLayout.Orientation.Portrait,
                                     MARGINS_MM, QPageLayout.Unit.Millimeter))
    document.print_(writer)
    if not path.is_file() or path.stat().st_size == 0:
        raise OSError(tr("The report could not be written to {0}.", path))


def previous_label(report: YearlyReport) -> str:
    previous = report.statistics.previous_period
    if report.is_complete:
        return str(previous.start.year)
    return f"{format_day_range(previous.start, previous.end)} {previous.start.year}"


def report_html(report: YearlyReport, *, charts: set[str] | None = None) -> str:
    charts = set() if charts is None else charts
    parts = [STYLE, _title(report), _summary(report), _months(report, MONTHS_URL in charts),
             _net_worth(report, NET_WORTH_URL in charts),
             _spending(report, SPENDING_URL in charts), _largest(report), _footer(report)]
    direction = " dir='rtl'" if is_right_to_left() else ""
    return f"<html><body{direction}>" + "".join(parts) + "</body></html>"


def _title(report: YearlyReport) -> str:
    span = (f"{format_date(report.period.start)} – {format_date(report.period.end)}"
            if not report.is_complete else tr("The whole year"))
    scope = span if report.is_complete else tr("{0}, year to date", span)
    return (f"<p class='muted small'>{tr('MONEY MANAGER · YEARLY REPORT')}</p>"
            f"<h1>{report.year}</h1><p class='muted'>"
            f"{tr('{0} · made on {1}', scope, format_date(report.generated_on))}</p>")


def _summary(report: YearlyReport) -> str:
    stats = report.statistics
    now, before = stats.totals, stats.previous_totals
    previous = previous_label(report) if stats.comparison_complete else None
    cells = []
    for label, value, prior, higher_is_good in (
        (tr("Income"), now.income, before.income, True),
        (tr("Spending"), now.spending, before.spending, False),
        (tr("Invested"), now.investments, before.investments, True),
        (tr("Saved"), now.savings, before.savings, True),
    ):
        change = ""
        if previous is not None:
            delta = value - prior
            tone = "" if delta.is_zero() else (
                "good" if delta.is_positive() == higher_is_good else "bad")
            change = (f"<br><span class='small {tone}'>{format_signed_money(delta)}"
                      f"</span><span class='small muted'> {tr('vs {0}', previous)}</span>")
        cells.append(f"<td width='25%'><p class='muted small'>{label.upper()}</p>"
                     f"<p class='kpi'>{format_money(value)}</p>{change}</td>")
    lines = []
    rate = now.savings_rate
    if rate is not None:
        lines.append(tr("You kept <b>{0}</b> of your income.", format_percent(rate))
                     if not now.savings.is_negative() else
                     tr("You spent <b>{0}</b> more than your income.",
                        format_money(-now.savings)))
    best, worst = report.best_month, report.worst_month
    if best is not None and worst is not None and best.month != worst.month:
        lines.append(tr("Best month: <b>{0}</b> ({1} kept). Hardest month: <b>{2}</b> ({3}).",
                        format_month(best.month), format_signed_money(best.totals.savings),
                        format_month(worst.month), format_signed_money(worst.totals.savings)))
    return (f"<h2>{tr('Summary')}</h2><table width='100%' cellpadding='4' cellspacing='0'><tr>"
            + "".join(cells) + "</tr></table>"
            + "".join(f"<p class='muted small'>{line}</p>" for line in lines))


def _months(report: YearlyReport, with_chart: bool) -> str:
    body = []
    for month in report.months:
        totals = month.totals
        rate = totals.savings_rate
        tone = "bad" if totals.savings.is_negative() else ""
        body.append(
            f"<tr><td>{format_month(month.month)}"
            f"{' ' + tr('(to date)') if month.is_partial else ''}"
            f"</td><td align='right'>{format_money(totals.income)}</td>"
            f"<td align='right'>{format_money(totals.spending)}</td>"
            f"<td align='right' class='{tone}'>{format_signed_money(totals.savings)}</td>"
            f"<td align='right'>{'—' if rate is None else format_percent(rate)}</td></tr>")
    chart = f"<p><img src='{MONTHS_URL}' width='{CHART_WIDTH_PX}'></p>" if with_chart else ""
    return (f"<h2>{tr('Month by month')}</h2>" + chart
            + f"<table class='data' width='100%' cellpadding='5'><tr><th>{tr('Month')}</th>"
            f"<th align='right'>{tr('Income')}</th><th align='right'>{tr('Spending')}</th>"
            f"<th align='right'>{tr('Saved')}</th><th align='right'>{tr('Savings rate')}</th>"
            "</tr>" + "".join(body) + "</table>")


def _net_worth(report: YearlyReport, with_chart: bool) -> str:
    if not report.net_worth:
        return ""
    first, last = report.net_worth[0], report.net_worth[-1]
    change = last.net_worth - first.net_worth
    chart = f"<p><img src='{NET_WORTH_URL}' width='{CHART_WIDTH_PX}'></p>" if with_chart else ""
    tone = "good" if not change.is_negative() else "bad"
    text = tr("From <b>{0}</b> at the end of {1} to <b>{2}</b> on {3} ({4}).",
              format_money(first.net_worth), format_month(first.month),
              format_money(last.net_worth), format_date(last.on),
              f"<span class='{tone}'>{format_signed_money(change)}</span>")
    return (f"<h2 style='page-break-before: always'>{tr('Net worth')}</h2><p>{text}</p>"
            + chart)


def _spending(report: YearlyReport, with_chart: bool) -> str:
    stats = report.statistics
    rows = stats.spending_by_category
    if not rows:
        return (f"<h2>{tr('Where the money went')}</h2>"
                f"<p class='muted'>{tr('No spending recorded.')}</p>")
    changes = {c.category_id: c for c in stats.category_changes}
    body = []
    for row in rows:
        change = changes.get(row.category_id)
        delta = ("—" if change is None or not stats.comparison_complete
                 else format_signed_money(change.change))
        share = "—" if row.share is None else format_percent(row.share)
        body.append(f"<tr><td>{escape(row.name)}</td><td align='right'>"
                    f"{format_money(row.amount)}</td><td align='right'>{share}</td>"
                    f"<td align='right'>{delta}</td></tr>")
    chart = f"<p><img src='{SPENDING_URL}' width='{CHART_WIDTH_PX}'></p>" if with_chart else ""
    return (f"<h2>{tr('Where the money went')}</h2>" + chart
            + f"<table class='data' width='100%' cellpadding='5'><tr><th>{tr('Category')}</th>"
            f"<th align='right'>{tr('Spent')}</th><th align='right'>{tr('Share')}</th>"
            f"<th align='right'>{tr('vs {0}', previous_label(report))}</th></tr>"
            + "".join(body) + "</table>")


def _largest(report: YearlyReport) -> str:
    if not report.largest_expenses:
        return ""
    body = []
    for t in report.largest_expenses:
        category = report.category_names.get(t.category_id, "—") if t.category_id else "—"
        body.append(f"<tr><td>{format_date(t.occurred_on)}</td><td>{escape(t.description)}</td>"
                    f"<td>{escape(category)}</td><td align='right'>{format_money(t.amount)}"
                    "</td></tr>")
    return (f"<h2>{tr('Largest expenses')}</h2>"
            f"<table class='data' width='100%' cellpadding='5'><tr><th>{tr('Date')}</th>"
            f"<th>{tr('Description')}</th><th>{tr('Category')}</th>"
            f"<th align='right'>{tr('Amount')}</th></tr>" + "".join(body) + "</table>")


def _footer(report: YearlyReport) -> str:
    text = tr("Made by Money Manager {0} on your computer from the entries you recorded. "
              "Amounts in {1}. Transfers between your accounts, loans and balance corrections "
              "are not counted as income or spending.", __version__, report.currency)
    return f"<p class='muted small' style='margin-top: 18px'>{text}</p>"


def months_chart(report: YearlyReport) -> QImage:
    figure = _figure(2.4)
    ax = figure.add_subplot()
    _style_axes(ax)
    xs = list(range(len(report.months)))
    width = 0.38
    income = [plot_value(m.totals.income) for m in report.months]
    spending = [plot_value(m.totals.spending) for m in report.months]
    ax.bar([x - width / 2 for x in xs], income, width=width, color=BAR, label=tr("Income"))
    ax.bar([x + width / 2 for x in xs], spending, width=width, color=SPEND,
           label=tr("Spending"))
    ax.set_xticks(xs, [month_abbreviation(m.month) for m in report.months])
    ax.yaxis.set_major_formatter(_compact)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), frameon=False, fontsize=8, ncols=2,
              borderaxespad=0.2, labelcolor=MUTED)
    return _image(figure)
