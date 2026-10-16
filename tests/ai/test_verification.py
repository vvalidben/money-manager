"""Numbers in AI answers are checked against the analysis they were based on."""

from datetime import date

import pytest

from money_manager.ai.verification import unsupported_numbers
from money_manager.domain.insights import AdvisorPeriod, advisor_range
from money_manager.domain.periods import DateRange

ANALYSIS = """\
Period: 2026-06-01 to 2026-06-15 (15 days)
- Income: 12,000.00 MAD (change: 0.0%)
- Expenses: 9,200.00 MAD (change: +18.0%)
- Savings: +2,800.00 MAD (savings rate: 23.3% of income)
- Food: 1,700.00 MAD -> 2,100.00 MAD (+23.5%)
- Leisure: 65.00 MAD (0.7%)
- Food: 2,100.00 MAD, 3.66x its average of 574.00 MAD over the previous 3 periods
"""


@pytest.mark.parametrize("answer", [
    # The requirements example: an approximate, rounded percentage from the data.
    "Food spending increased by approximately 24% compared with last month. You may want to "
    "review restaurant and delivery expenses.",
    "Food rose from 1,700.00 MAD to 2,100.00 MAD (+23.5%).",
    "Your income was 12,000 MAD and your savings rate about 23%.",
    "Expenses were roughly 9,200 MAD, up 18%.",
    "Savings were 2,800 MAD. Leisure cost 65 MAD.",
    "Food is 3.66 times its usual level.",
    "Expenses decreased by -18.0%?",  # the sign is not what is checked
])
def test_numbers_from_the_analysis_pass(answer: str) -> None:
    assert unsupported_numbers(answer, ANALYSIS) == ()


def test_invented_or_calculated_numbers_are_reported() -> None:
    answer = ("You spent 2,700 MAD on restaurants, 30% of your expenses. "
              "Food and leisure together cost 2,165.00 MAD. Cutting 30% saves more.")
    assert unsupported_numbers(answer, ANALYSIS) == ("2,700", "30%", "2,165.00")


@pytest.mark.parametrize("answer", [
    "Over the last 3 months across 2 categories in 2026 …",
    "Between 2026-06-01 and 2026-06-15 your spending rose.",
    "1. Review subscriptions\n2. Plan meals",
])
def test_counts_years_dates_and_list_numbers_are_ignored(answer: str) -> None:
    assert unsupported_numbers(answer, ANALYSIS) == ()


def test_rounding_is_limited() -> None:
    # 9,200.00 may be called "about 9,000" (within 5%), but not "about 8,000".
    assert unsupported_numbers("about 9,000 MAD", ANALYSIS) == ()
    assert unsupported_numbers("about 8,000 MAD", ANALYSIS) == ("8,000",)
    assert unsupported_numbers("23.6%", ANALYSIS) == ("23.6%",)  # precise but not in the data


@pytest.mark.parametrize(("period", "expected"), [
    (AdvisorPeriod.THIS_MONTH, DateRange(date(2026, 6, 1), date(2026, 6, 15))),
    (AdvisorPeriod.LAST_MONTH, DateRange(date(2026, 5, 1), date(2026, 5, 31))),
    (AdvisorPeriod.LAST_3_MONTHS, DateRange(date(2026, 3, 16), date(2026, 6, 15))),
    (AdvisorPeriod.LAST_12_MONTHS, DateRange(date(2025, 6, 16), date(2026, 6, 15))),
])
def test_advisor_periods(period: AdvisorPeriod, expected: DateRange) -> None:
    assert advisor_range(period, date(2026, 6, 15)) == expected
