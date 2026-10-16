"""Statistics and the financial analysis, recomputed by brute force from the raw
transactions for many ranges (presets, month ends, leap days, random ranges)."""

import random
from collections import defaultdict
from datetime import date, timedelta

import pytest

from money_manager.domain.entities import Transaction, TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.money import Money
from money_manager.domain.periods import (
    DateRange,
    StatsRange,
    month_end,
    month_start,
    previous_range,
    rolling_range,
)
from money_manager.services import AppServices
from tests.services.support import TODAY

OPENING = date(2025, 1, 1)
OPENING_MINOR = 1_000_000


@pytest.fixture
def world(app_services: AppServices) -> tuple[AppServices, list[Transaction], frozenset[int]]:
    s = app_services
    rng = random.Random(42)
    bank = s.accounts.create("Bank", opening_balance="10000", opening_date=OPENING)
    salary = s.categories.create("Salary", CategoryKind.INCOME)
    bonus = s.categories.create("Bonus", CategoryKind.INCOME)
    expense_categories = [s.categories.create(n, CategoryKind.EXPENSE)
                          for n in ("Food", "Rent", "Travel", "Stocks")]
    s.categories.set_investment(expense_categories[3].id, True)
    for _ in range(600):
        day = OPENING + timedelta(days=rng.randrange((TODAY - OPENING).days + 1))
        roll = rng.random()
        if roll < 0.12:
            kind, category = TransactionType.INCOME, rng.choice([salary, bonus]).id
        elif roll < 0.95:
            kind, category = TransactionType.EXPENSE, rng.choice(expense_categories).id
        else:
            kind = rng.choice([TransactionType.ADJUSTMENT_IN, TransactionType.ADJUSTMENT_OUT])
            category = None
        cents = rng.randint(1, 900_000)
        s.transactions.create(TransactionDraft(bank.id, kind, f"{cents // 100}.{cents % 100:02d}",
                                               day, category))
    return s, s.transactions.list(), frozenset({expense_categories[3].id})


def sums(items: list[Transaction], period: DateRange, investments: frozenset[int]) -> dict:
    inside = [t for t in items if period.start <= t.occurred_on <= period.end]
    total = defaultdict(int)
    by_category: defaultdict[int, int] = defaultdict(int)
    for t in inside:
        total[t.type] += t.amount.minor_units
        if t.type is TransactionType.EXPENSE:
            if t.category_id in investments:
                total["investments"] += t.amount.minor_units
            else:
                by_category[t.category_id] += t.amount.minor_units
    spending = total[TransactionType.EXPENSE] - total["investments"]
    net = (total[TransactionType.INCOME] + total[TransactionType.ADJUSTMENT_IN]
           - total[TransactionType.EXPENSE] - total[TransactionType.ADJUSTMENT_OUT])
    return {"income": total[TransactionType.INCOME], "expenses": total[TransactionType.EXPENSE],
            "investments": total["investments"], "spending": spending,
            "savings": total[TransactionType.INCOME] - spending, "net": net,
            "by_category": dict(by_category)}


def balance_at(items: list[Transaction], day: date) -> int:
    if day < OPENING:
        return 0  # the account did not exist yet
    return OPENING_MINOR + sum(t.type.sign * t.amount.minor_units for t in items
                               if t.occurred_on <= day)


def ranges() -> list[DateRange]:
    rng = random.Random(7)
    found = [rolling_range(preset, TODAY) for preset in StatsRange if preset is not StatsRange.CUSTOM]
    found += [DateRange(date(2026, 2, 1), date(2026, 2, 28)),  # a whole February
              DateRange(date(2025, 12, 31), date(2026, 1, 1)),  # across a year end
              DateRange(date(2026, 1, 31), date(2026, 3, 31)),  # month ends
              DateRange(OPENING, TODAY),  # everything
              DateRange(TODAY, TODAY)]
    for _ in range(12):
        start = OPENING + timedelta(days=rng.randrange(500))
        end = min(TODAY, start + timedelta(days=rng.randrange(1, 400)))
        found.append(DateRange(start, end))
    return found


@pytest.mark.parametrize("period", ranges(), ids=lambda r: f"{r.start}_{r.end}")
def test_statistics_match_brute_force(world, period: DateRange) -> None:  # noqa: ANN001
    s, items, investments = world
    report = s.statistics.report(period)
    expected = sums(items, period, investments)
    totals = report.totals

    assert totals.income.minor_units == expected["income"]
    assert totals.expenses.minor_units == expected["expenses"]
    assert totals.investments.minor_units == expected["investments"]
    assert totals.spending.minor_units == expected["spending"]
    assert totals.savings.minor_units == expected["savings"]
    assert totals.net_change.minor_units == expected["net"]
    assert {c.category_id: c.amount.minor_units for c in report.spending_by_category} == (
        expected["by_category"])
    assert sum(b.spending.minor_units for b in report.trend.buckets) == expected["spending"]

    previous = sums(items, previous_range(period), investments)
    assert report.previous_totals.expenses.minor_units == previous["expenses"]
    assert report.balance.opening.minor_units == balance_at(items, period.start - timedelta(1))
    assert report.balance.closing.minor_units == balance_at(items, period.end)

    for summary in report.months:
        month = DateRange(summary.month, min(month_end(summary.month), period.end))
        month_sums = sums(items, month, investments)
        assert summary.totals.income.minor_units == month_sums["income"]
        assert summary.totals.expenses.minor_units == month_sums["expenses"]
    assert report.months[0].month == month_start(period.start)
    assert report.months[-1].month == month_start(period.end)


@pytest.mark.parametrize("period", ranges()[:10], ids=lambda r: f"{r.start}_{r.end}")
def test_financial_analysis_matches_brute_force(world, period: DateRange) -> None:  # noqa: ANN001
    s, items, investments = world
    analysis = s.analysis.analyze(period)
    expected = sums(items, period, investments)
    comparison = sums(items, analysis.comparison_period, investments)

    assert analysis.period_income.minor_units == expected["income"]
    assert analysis.period_expenses.minor_units == expected["expenses"]
    assert analysis.savings_amount.minor_units == expected["savings"]
    assert analysis.net_change.minor_units == expected["net"]
    assert analysis.current_balance.minor_units == balance_at(items, period.end)
    assert analysis.comparison_totals.expenses.minor_units == comparison["expenses"]
    if expected["income"]:
        spent = Money.from_minor_units(expected["spending"])
        assert analysis.spending_ratio == (spent.amount / Money.from_minor_units(
            expected["income"]).amount).quantize(analysis.spending_ratio)
    shares = [c.share for c in analysis.spending_by_category if c.share is not None]
    if shares:
        assert abs(sum(shares) - 1) <= len(shares) * analysis.spending_by_category[0].share.scaleb(-4)
