from datetime import date
from decimal import Decimal

import pytest

from money_manager.core.errors import ValidationError
from money_manager.domain.investments import (
    EntryKind,
    Investment,
    InvestmentEntry,
    InvestmentKind,
    InvestmentPosition,
    PortfolioSummary,
    Valuation,
)
from money_manager.domain.money import Money
from money_manager.domain.validation import validate_investment

ETF = Investment(1, "World ETF", InvestmentKind.ETF, "")
_ids = iter(range(1, 10_000))


def contribution(amount: str, on: date, investment: int = 1) -> InvestmentEntry:
    return InvestmentEntry(next(_ids), investment, EntryKind.CONTRIBUTION, Money.of(amount), on, "")


def withdrawal(amount: str, on: date, investment: int = 1) -> InvestmentEntry:
    return InvestmentEntry(next(_ids), investment, EntryKind.WITHDRAWAL, Money.of(amount), on, "")


def value(amount: str, on: date, investment: int = 1) -> Valuation:
    return Valuation(next(_ids), investment, on, Money.of(amount), "")


def position(entries=(), valuations=(), investment: Investment = ETF) -> InvestmentPosition:
    return InvestmentPosition(investment, tuple(entries), tuple(valuations), "MAD")


class TestPosition:
    def test_profit_and_return(self) -> None:
        item = position(
            [contribution("1000", date(2026, 1, 5)), contribution("500", date(2026, 3, 5))],
            [value("1650", date(2026, 6, 1))],
        )

        assert item.contributed == Money.of("1500") and item.net_invested == Money.of("1500")
        assert item.current_value == Money.of("1650")
        assert item.profit == Money.of("150")  # current value − contributed
        assert item.return_ratio == Decimal("0.1000")  # 150 ÷ 1,500 = 10 %

    def test_loss(self) -> None:
        item = position([contribution("2000", date(2026, 1, 5))], [value("1700", date(2026, 2, 1))])

        assert item.profit == Money.of("-300")
        assert item.return_ratio == Decimal("-0.1500")

    def test_no_valuation_means_no_return(self) -> None:
        item = position([contribution("2000", date(2026, 1, 5))])

        assert item.current_value is None and item.profit is None and item.return_ratio is None
        assert not item.is_value_current

    def test_out_of_date_value_means_no_return(self) -> None:
        item = position(
            [contribution("1000", date(2026, 1, 5)), contribution("500", date(2026, 6, 10))],
            [value("1100", date(2026, 6, 1))],  # taken before the latest contribution
        )

        assert item.current_value == Money.of("1100")  # still shown …
        assert not item.is_value_current
        assert item.profit is None and item.return_ratio is None  # … but no return

    def test_value_on_the_same_day_as_the_contribution_is_current(self) -> None:
        item = position([contribution("100", date(2026, 6, 1))], [value("100", date(2026, 6, 1))])
        assert item.is_value_current and item.profit == Money.zero()

    def test_latest_valuation_wins(self) -> None:
        item = position([contribution("100", date(2026, 1, 1))],
                        [value("90", date(2026, 3, 1)), value("130", date(2026, 5, 1)),
                         value("110", date(2026, 4, 1))])
        assert item.current_value == Money.of("130")

    def test_withdrawals_reduce_net_invested(self) -> None:
        item = position(
            [contribution("1000", date(2026, 1, 1)), withdrawal("400", date(2026, 2, 1))],
            [value("660", date(2026, 3, 1))],
        )

        assert (item.withdrawn, item.net_invested) == (Money.of("400"), Money.of("600"))
        assert item.profit == Money.of("60") and item.return_ratio == Decimal("0.1000")

    def test_withdrawing_more_than_invested_has_profit_but_no_percentage(self) -> None:
        item = position(
            [contribution("1000", date(2026, 1, 1)), withdrawal("1500", date(2026, 2, 1))],
            [value("200", date(2026, 3, 1))],
        )

        assert item.net_invested == Money.of("-500")
        assert item.profit == Money.of("700")
        assert item.return_ratio is None  # no positive amount at risk to divide by

    def test_valued_without_contributions(self) -> None:
        item = position([], [value("500", date(2026, 3, 1))])
        assert item.profit == Money.of("500") and item.return_ratio is None

    def test_rounding_and_precision(self) -> None:
        item = position([contribution("3", date(2026, 1, 1))], [value("4", date(2026, 1, 2))])
        assert item.return_ratio == Decimal("0.3333")
        tiny = position([contribution("0.03", date(2026, 1, 1))],
                        [value("0.04", date(2026, 1, 2))])
        assert tiny.profit == Money.of("0.01") and tiny.return_ratio == Decimal("0.3333")

    def test_empty(self) -> None:
        item = position()
        assert item.net_invested == Money.zero() and item.last_activity is None
        assert item.profit is None


class TestPortfolio:
    def test_totals_and_net_worth(self) -> None:
        etf = position([contribution("1000", date(2026, 1, 1))], [value("1200", date(2026, 2, 1))])
        gold = position([contribution("500", date(2026, 1, 1), 2)],
                        [value("450", date(2026, 2, 1), 2)],
                        Investment(2, "Gold", InvestmentKind.GOLD, ""))
        stale = position([contribution("300", date(2026, 5, 1), 3)],
                         [value("280", date(2026, 4, 1), 3)],
                         Investment(3, "Bitcoin", InvestmentKind.CRYPTO, ""))
        unvalued = position([contribution("100", date(2026, 1, 1), 4)], [],
                            Investment(4, "Friend's shop", InvestmentKind.OTHER, ""))

        summary = PortfolioSummary((etf, gold, stale, unvalued), Money.of("10000"), "MAD")

        assert summary.contributed == Money.of("1900")
        assert summary.total_value == Money.of("1930")  # never-valued investment not counted
        assert len(summary.valued) == 3
        assert summary.total_profit == Money.of("150")  # only up-to-date values: +200 − 50
        assert summary.return_ratio == Decimal("0.1000")  # 150 ÷ 1,500
        assert summary.net_worth == Money.of("11930")
        assert [(k.kind, k.value) for k in summary.by_kind] == [
            (InvestmentKind.ETF, Money.of("1200")),
            (InvestmentKind.GOLD, Money.of("450")),
            (InvestmentKind.CRYPTO, Money.of("280")),
        ]

    def test_insufficient_data(self) -> None:
        summary = PortfolioSummary(
            (position([contribution("100", date(2026, 1, 1))]),), Money.zero(), "MAD")

        assert summary.total_value == Money.zero()
        assert summary.total_profit is None and summary.return_ratio is None
        assert summary.by_kind == ()


class TestValidation:
    def test_valid(self) -> None:
        valid = validate_investment(name="  Apple ", kind=" STOCK", notes=None)
        assert (valid.name, valid.kind, valid.notes) == ("Apple", InvestmentKind.STOCK, "")

    @pytest.mark.parametrize(("name", "kind", "field"),
                             [("", "stock", "name"), ("Apple", "bond", "kind"),
                              ("Apple", None, "kind")])
    def test_invalid(self, name: str, kind: object, field: str) -> None:
        with pytest.raises(ValidationError) as info:
            validate_investment(name=name, kind=kind, notes="")
        assert info.value.field == field
