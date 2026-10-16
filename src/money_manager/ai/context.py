"""Financial-analysis context for an AI model.

The model receives the *results* of the deterministic engine
(``domain.financial_analysis``) as a short labelled text, never the database
or individual transactions. What is never included, by construction:

* transaction descriptions and notes (free text that may name people or places),
* recurring-expense labels (they are derived from descriptions),
* account, allocation, goal, subscription and investment names,
* database identifiers and the dates of individual expenses.

Category names are included by default because advice about "Food" is more
useful than about "Category A"; ``ContextOptions`` can replace them with
neutral labels and leave out the balance.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from money_manager.domain.analytics import TrendDirection
from money_manager.domain.financial_analysis import (
    BASELINE_PERIODS,
    FinancialAnalysis,
    MetricTrend,
    UnusualKind,
    money_text,
    percent_text,
    range_text,
)
from money_manager.domain.money import Money, sum_money

MAX_CATEGORIES = 8
MAX_CATEGORY_CHANGES = 8
MAX_MONTHS = 12

NEVER_SENT = (
    "transaction descriptions and notes",
    "individual transactions and their dates",
    "account, allocation, goal, subscription and investment names",
    "recurring-expense labels",
)


@dataclass(frozen=True, slots=True)
class ContextOptions:
    include_category_names: bool = True
    include_balance: bool = True


@dataclass(frozen=True, slots=True)
class FinancialContext:
    text: str
    options: ContextOptions
    currency: str

    @property
    def included(self) -> tuple[str, ...]:
        """Plain-language list of what the text contains (for the privacy notice)."""
        items = ["income, expenses, savings and investment totals and rates",
                 "spending per category and changes against the comparison period",
                 "monthly totals and trends", "unusual spending and recurring-spending totals"]
        if self.options.include_balance:
            items.insert(0, "your total balance")
        items.append("category names" if self.options.include_category_names
                     else "categories as neutral labels (Category A, B, …)")
        return tuple(items)


class _CategoryLabels:
    """Real names, or stable neutral labels in order of first appearance."""

    def __init__(self, real: bool) -> None:
        self._real = real
        self._labels: dict[str, str] = {}

    def __call__(self, name: str) -> str:
        if self._real:
            return name
        if name not in self._labels:
            self._labels[name] = f"Category {_letters(len(self._labels))}"
        return self._labels[name]


def _letters(index: int) -> str:
    text = ""
    index += 1
    while index:
        index, rest = divmod(index - 1, 26)
        text = chr(ord("A") + rest) + text
    return text


def _pct(value: Decimal | None, *, signed: bool = False) -> str:
    return "n/a" if value is None else percent_text(value, signed=signed)


def _signed(value: Money) -> str:
    return ("+" if value.is_positive() else "") + money_text(value)


def _trend(label: str, trend: MetricTrend) -> str:
    if trend.direction is TrendDirection.NO_DATA:
        return f"- {label}: not enough complete months"
    change = "" if trend.change is None else f" ({percent_text(trend.change, signed=True)})"
    values = ", ".join(f"{v.month.isoformat()[:7]} {money_text(v.value)}" for v in trend.series)
    return f"- {label}: {trend.direction.value}{change}; {values}"


def build_financial_context(analysis: FinancialAnalysis,
                            options: ContextOptions = ContextOptions()) -> FinancialContext:
    currency = analysis.current_balance.currency
    label = _CategoryLabels(options.include_category_names)
    totals = analysis.totals
    lines: list[str] = [
        f"Financial analysis (computed on the user's computer by fixed rules; currency "
        f"{currency})",
        f"Period: {range_text(analysis.period)} ({analysis.period.days} days)",
    ]
    if analysis.comparison_complete:
        lines.append(f"Comparison period: {range_text(analysis.comparison_period)}")
    else:
        lines.append("Comparison period: not available (it starts before tracking began)")

    lines += ["", "Totals",
              f"- Income: {money_text(totals.income)} "
              f"(change: {_pct(analysis.income_change, signed=True)})",
              f"- Expenses: {money_text(totals.expenses)} "
              f"(change: {_pct(analysis.expenses_change, signed=True)})",
              f"- Spending (expenses excluding investments): {money_text(totals.spending)} "
              f"(change: {_pct(analysis.spending_change, signed=True)})",
              f"- Investment contributions: {money_text(totals.investments)} "
              f"(investment rate: {_pct(analysis.investment_rate)} of income)",
              f"- Savings: {_signed(totals.savings)} "
              f"(savings rate: {_pct(analysis.savings_rate)} of income)",
              f"- Spending ratio: {_pct(analysis.spending_ratio)} of income",
              f"- Net change of the balance: {_signed(totals.net_change)}"]
    if options.include_balance:
        lines.append(f"- Balance at the end of the period: {money_text(analysis.current_balance)}")
    largest = analysis.largest_expense_category
    if largest is not None:
        lines.append(f"- Largest spending category: {label(largest.name)} "
                     f"({_pct(largest.share)} of spending)")

    lines += ["", "Spending by category (investments excluded)"]
    lines += _category_lines(analysis, label) or ["- no spending recorded"]

    if analysis.comparison_complete and analysis.category_changes:
        lines += ["", "Category changes against the comparison period"]
        for change in analysis.category_changes[:MAX_CATEGORY_CHANGES]:
            name = label(change.name)
            if change.is_new:
                lines.append(f"- {name}: {money_text(change.current)} (none in the comparison "
                             "period)")
            else:
                lines.append(f"- {name}: {money_text(change.previous)} -> "
                             f"{money_text(change.current)} "
                             f"({_pct(change.change_ratio, signed=True)})")

    if analysis.monthly:
        lines += ["", "Months"]
        for month in analysis.monthly[-MAX_MONTHS:]:
            partial = " (to date)" if month.is_partial else ""
            lines.append(
                f"- {month.month.isoformat()[:7]}{partial}: income "
                f"{money_text(month.totals.income)}, expenses "
                f"{money_text(month.totals.expenses)}, savings rate "
                f"{_pct(month.totals.savings_rate)}, spending change vs previous month "
                f"{_pct(month.spending_change, signed=True)}")

    lines += ["", "Trends over complete months (newer half vs older half; ±5% = stable)",
              _trend("Income", analysis.income_trend),
              _trend("Spending", analysis.expense_trend)]
    if options.include_balance:
        lines.append(_trend("Month-end balance", analysis.balance_trend))

    lines += ["", "Unusual spending"]
    lines += _unusual_lines(analysis, label) or ["- none detected"]

    recurring = analysis.recurring
    lines += ["", "Recurring spending (detected over the last 12 months)"]
    if recurring.detected:
        share = ("" if recurring.share_of_monthly_spending is None else
                 f", {percent_text(recurring.share_of_monthly_spending)} of average monthly "
                 "spending")
        count, untracked = len(recurring.detected), len(recurring.untracked)
        lines.append(f"- {count} recurring {'expense' if count == 1 else 'expenses'}, about "
                     f"{money_text(recurring.detected_monthly_total)} per month{share}")
        lines.append(f"- {untracked} of them {'is' if untracked == 1 else 'are'} not tracked "
                     "as subscriptions")
    else:
        lines.append("- none detected")
    lines.append(f"- Declared subscriptions: {money_text(recurring.subscriptions_monthly_total)} "
                 "per month")
    return FinancialContext("\n".join(lines), options, currency)


def _category_lines(analysis: FinancialAnalysis, label: _CategoryLabels) -> list[str]:
    rows = analysis.spending_by_category
    lines = [f"- {label(row.name)}: {money_text(row.amount)} ({_pct(row.share)})"
             for row in rows[:MAX_CATEGORIES]]
    rest = rows[MAX_CATEGORIES:]
    if rest:
        amount = sum_money((row.amount for row in rest), rows[0].amount.currency)
        shares: Iterable[Decimal] = (row.share for row in rest if row.share is not None)
        lines.append(f"- {len(rest)} other categories: {money_text(amount)} "
                     f"({_pct(sum(shares, Decimal(0)))})")
    return lines


def _unusual_lines(analysis: FinancialAnalysis, label: _CategoryLabels) -> list[str]:
    lines = []
    for item in analysis.unusual_spending:
        name = label(item.category_name)
        match item.kind:
            case UnusualKind.CATEGORY_SPIKE:
                lines.append(f"- {name}: {money_text(item.amount)}, {item.factor}x its average "
                             f"of {money_text(item.baseline)} over the previous "
                             f"{BASELINE_PERIODS} periods")
            case UnusualKind.NEW_CATEGORY:
                lines.append(f"- {name}: {money_text(item.amount)}, no spending in the previous "
                             f"{BASELINE_PERIODS} periods")
            case UnusualKind.LARGE_EXPENSE:
                lines.append(f"- One {name} expense of {money_text(item.amount)}, {item.factor}x "
                             f"the category's typical expense of {money_text(item.baseline)}")
    return lines
