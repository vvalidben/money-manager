"""Named date ranges such as "this month", resolved against a given today."""

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum
from money_manager.core.i18n import tr


@dataclass(frozen=True, slots=True)
class DateRange:
    """Inclusive range of calendar days."""

    start: date
    end: date

    def __post_init__(self) -> None:
        if self.start > self.end:
            raise ValueError(tr("start must not be after end"))

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    def __contains__(self, day: object) -> bool:
        return isinstance(day, date) and self.start <= day <= self.end


def month_start(day: date) -> date:
    return day.replace(day=1)


def month_end(day: date) -> date:
    return day.replace(day=monthrange(day.year, day.month)[1])


def add_months(day: date, months: int) -> date:
    """First day of the month ``months`` away from ``day``'s month."""
    index = day.year * 12 + (day.month - 1) + months
    return date(index // 12, index % 12 + 1, 1)


def shift_months(day: date, months: int) -> date:
    """The same day number ``months`` away, clamped to the target month's length."""
    first = add_months(day, months)
    return first.replace(day=min(day.day, month_end(first).day))


class StatsRange(StrEnum):
    DAYS_7 = "7d"
    DAYS_30 = "30d"
    MONTHS_3 = "3m"
    MONTHS_6 = "6m"
    YEAR_1 = "1y"
    CUSTOM = "custom"


def rolling_range(preset: StatsRange, today: date) -> DateRange:
    """Trailing window ending today (inclusive), e.g. 30 days = today and the 29 before.

    Month-based windows start the day after the same date N months ago, so
    "3 months" on 15 Jun covers 16 Mar – 15 Jun.
    """
    match preset:
        case StatsRange.DAYS_7:
            return DateRange(today - timedelta(days=6), today)
        case StatsRange.DAYS_30:
            return DateRange(today - timedelta(days=29), today)
        case StatsRange.MONTHS_3:
            return DateRange(shift_months(today, -3) + timedelta(days=1), today)
        case StatsRange.MONTHS_6:
            return DateRange(shift_months(today, -6) + timedelta(days=1), today)
        case StatsRange.YEAR_1:
            return DateRange(shift_months(today, -12) + timedelta(days=1), today)
        case StatsRange.CUSTOM:
            raise ValueError(tr("A custom range has no preset dates."))


def previous_range(period: DateRange) -> DateRange:
    """The equally long range immediately before ``period``."""
    end = period.start - timedelta(days=1)
    return DateRange(end - timedelta(days=period.days - 1), end)


def month_to_date(today: date) -> DateRange:
    return DateRange(month_start(today), today)


def same_days_previous_month(today: date) -> DateRange:
    """Day 1 up to today's day number in the previous month (clamped to its length).

    Used to compare month-to-date figures fairly, e.g. 1–15 Mar vs 1–15 Feb.
    """
    start = add_months(today, -1)
    return DateRange(start, min(start + timedelta(days=today.day - 1), month_end(start)))


class DatePreset(StrEnum):
    ALL_TIME = "all_time"
    THIS_MONTH = "this_month"
    LAST_MONTH = "last_month"
    LAST_30_DAYS = "last_30_days"
    THIS_YEAR = "this_year"
    LAST_YEAR = "last_year"
    CUSTOM = "custom"


def preset_range(preset: DatePreset, today: date) -> tuple[date | None, date | None]:
    """Inclusive (start, end); ``None`` means unbounded. CUSTOM has no fixed range."""
    first_of_month = today.replace(day=1)
    match preset:
        case DatePreset.ALL_TIME | DatePreset.CUSTOM:
            return None, None
        case DatePreset.THIS_MONTH:
            return first_of_month, today
        case DatePreset.LAST_MONTH:
            last_of_previous = first_of_month - timedelta(days=1)
            return last_of_previous.replace(day=1), last_of_previous
        case DatePreset.LAST_30_DAYS:
            return today - timedelta(days=29), today
        case DatePreset.THIS_YEAR:
            return date(today.year, 1, 1), today
        case DatePreset.LAST_YEAR:
            return date(today.year - 1, 1, 1), date(today.year - 1, 12, 31)
