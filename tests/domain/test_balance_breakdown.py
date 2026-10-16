from money_manager.domain.balance import BalanceBreakdown
from money_manager.domain.enums import TransactionType
from money_manager.domain.money import Money


def test_formula() -> None:
    breakdown = BalanceBreakdown(
        opening_balance=Money.of("1000"),
        income=Money.of("12000"),
        expenses=Money.of("2500"),
        adjustments_in=Money.of("50.25"),
        adjustments_out=Money.of("10.10"),
    )

    # 1000 + 12000 − 2500 + 50.25 − 10.10
    assert breakdown.balance == Money.of("10540.15")


def test_from_totals_treats_missing_types_as_zero() -> None:
    breakdown = BalanceBreakdown.from_totals(Money.of("100"), {TransactionType.EXPENSE: 2550})

    assert breakdown.income == Money.zero()
    assert breakdown.expenses == Money.of("25.50")
    assert breakdown.balance == Money.of("74.50")


def test_balance_can_go_negative() -> None:
    breakdown = BalanceBreakdown.from_totals(Money.zero(), {TransactionType.EXPENSE: 100})

    assert breakdown.balance == Money.of("-1.00")


def test_keeps_currency_of_opening_balance() -> None:
    breakdown = BalanceBreakdown.from_totals(Money.of("1", "EUR"), {TransactionType.INCOME: 1})

    assert breakdown.balance == Money.of("1.01", "EUR")
