from datetime import date
from decimal import Decimal

import pytest

from money_manager.core.errors import ValidationError
from money_manager.domain.money import parse_amount_text
from money_manager.domain.periods import DatePreset, preset_range


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1200", "1200.00"),
        ("1 200", "1200.00"),
        ("1 200,50", "1200.50"),  # non-breaking space, French decimal comma
        ("1 200.5", "1200.50"),  # narrow no-break space
        ("12,5", "12.50"),
        ("0.01", "0.01"),
        (" 300 ", "300.00"),
        ("-300", "-300.00"),
        (".5", "0.50"),
        ("12.", "12.00"),
    ],
)
def test_accepted(text: str, expected: str) -> None:
    assert parse_amount_text(text) == Decimal(expected)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("", "Enter an amount"),
        ("   ", "Enter an amount"),
        ("1,200", "ambiguous"),
        ("1.200", "ambiguous"),
        ("1,200.50", "either a comma or a dot"),
        ("1.200,50", "either a comma or a dot"),
        ("1.200.000", "spaces"),
        ("1e3", "not a valid amount"),
        ("12abc", "not a valid amount"),
        ("NaN", "not a valid amount"),
        ("1.234", "ambiguous"),
        ("1.2345", "2 decimal places"),
    ],
)
def test_rejected(text: str, message: str) -> None:
    with pytest.raises(ValidationError, match=message) as info:
        parse_amount_text(text)
    assert info.value.field == "amount"


def test_non_text_is_rejected() -> None:
    with pytest.raises(ValidationError):
        parse_amount_text(12.5)


TODAY = date(2026, 3, 15)


@pytest.mark.parametrize(
    ("preset", "expected"),
    [
        (DatePreset.ALL_TIME, (None, None)),
        (DatePreset.CUSTOM, (None, None)),
        (DatePreset.THIS_MONTH, (date(2026, 3, 1), TODAY)),
        (DatePreset.LAST_MONTH, (date(2026, 2, 1), date(2026, 2, 28))),
        (DatePreset.LAST_30_DAYS, (date(2026, 2, 14), TODAY)),
        (DatePreset.THIS_YEAR, (date(2026, 1, 1), TODAY)),
        (DatePreset.LAST_YEAR, (date(2025, 1, 1), date(2025, 12, 31))),
    ],
)
def test_presets(preset: DatePreset, expected: tuple[date | None, date | None]) -> None:
    assert preset_range(preset, TODAY) == expected


def test_last_month_across_year_boundary() -> None:
    assert preset_range(DatePreset.LAST_MONTH, date(2026, 1, 10)) == (
        date(2025, 12, 1), date(2025, 12, 31)
    )


def test_last_30_days_is_inclusive() -> None:
    start, end = preset_range(DatePreset.LAST_30_DAYS, TODAY)
    assert start is not None and end is not None
    assert (end - start).days + 1 == 30
