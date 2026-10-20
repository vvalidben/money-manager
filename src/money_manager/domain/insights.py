"""AI insights: what was asked, about which period, and what the AI answered.

An insight is an interpretation of figures that the deterministic engine
(``domain.financial_analysis``) calculated; the AI never computes them. The
record keeps the exact analysis text the AI was given, so every answer can be
checked against its source.
"""

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from money_manager.core.i18n import tr
from money_manager.domain.periods import (
    DateRange,
    StatsRange,
    add_months,
    month_end,
    month_start,
    month_to_date,
    rolling_range,
)

MAX_HISTORY = 200  # older insights are removed when a new one is stored
MAX_ANSWER_LENGTH = 100_000


class InsightKind(StrEnum):
    INSIGHTS = "insights"
    SUGGESTIONS = "suggestions"
    SPENDING = "spending"
    MONTHLY = "monthly"
    QUESTION = "question"


KIND_LABELS = {
    InsightKind.INSIGHTS: "Insights",
    InsightKind.SUGGESTIONS: "Suggestions",
    InsightKind.SPENDING: "Spending analysis",
    InsightKind.MONTHLY: "Monthly summary",
    InsightKind.QUESTION: "Question",
}


class AdvisorPeriod(StrEnum):
    THIS_MONTH = "this_month"
    LAST_MONTH = "last_month"
    LAST_3_MONTHS = "last_3_months"
    LAST_12_MONTHS = "last_12_months"


PERIOD_LABELS = {
    AdvisorPeriod.THIS_MONTH: "This month",
    AdvisorPeriod.LAST_MONTH: "Last month",
    AdvisorPeriod.LAST_3_MONTHS: "Last 3 months",
    AdvisorPeriod.LAST_12_MONTHS: "Last 12 months",
}


def advisor_range(period: AdvisorPeriod, today: date) -> DateRange:
    match period:
        case AdvisorPeriod.THIS_MONTH:
            return month_to_date(today)
        case AdvisorPeriod.LAST_MONTH:
            first = add_months(month_start(today), -1)
            return DateRange(first, month_end(first))
        case AdvisorPeriod.LAST_3_MONTHS:
            return rolling_range(StatsRange.MONTHS_3, today)
        case AdvisorPeriod.LAST_12_MONTHS:
            return rolling_range(StatsRange.YEAR_1, today)


@dataclass(frozen=True, slots=True)
class Insight:
    id: int
    kind: InsightKind
    question: str  # the user's question; empty for the fixed tasks
    period: DateRange
    provider: str
    model: str
    is_online: bool  # the analysis was sent to an external provider
    answer: str
    context: str  # the exact analysis and task the AI received
    truncated: bool
    created_at: datetime  # UTC

    @property
    def title(self) -> str:
        if self.kind is InsightKind.QUESTION:
            return self.question
        return tr(KIND_LABELS[self.kind])
