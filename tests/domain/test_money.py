from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from money_manager.core.errors import CurrencyMismatchError, ValidationError
from money_manager.domain.money import (
    MAX_ABS_AMOUNT,
    MAX_STORABLE_AMOUNT,
    Money,
    parse_amount,
    sum_money,
)


class TestParseAmount:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("12.50", Decimal("12.50")),
            ("12.5", Decimal("12.50")),
            (" 7 ", Decimal("7.00")),
            (Decimal("0.01"), Decimal("0.01")),
            (Decimal("1.500"), Decimal("1.50")),  # trailing zeros are not extra precision
            (12000, Decimal("12000.00")),
            ("-300", Decimal("-300.00")),
            ("1E+3", Decimal("1000.00")),
        ],
    )
    def test_accepts_exact_values(self, raw: object, expected: Decimal) -> None:
        result = parse_amount(raw)

        assert result == expected
        assert result.as_tuple().exponent == -2

    @pytest.mark.parametrize("raw", [0.1, 12.0, float("nan")])
    def test_rejects_floats(self, raw: float) -> None:
        with pytest.raises(ValidationError, match="float"):
            parse_amount(raw)

    @pytest.mark.parametrize(
        "raw",
        ["", "   ", "abc", "12,50", "1.2.3", None, True, [1], "NaN", "Infinity", "-inf",
         Decimal("NaN"), Decimal("Infinity")],
    )
    def test_rejects_non_numbers(self, raw: object) -> None:
        with pytest.raises(ValidationError):
            parse_amount(raw)

    @pytest.mark.parametrize("raw", ["1.005", "0.001", Decimal("12.345"), "1E-5"])
    def test_rejects_more_than_two_decimals_instead_of_rounding(self, raw: object) -> None:
        with pytest.raises(ValidationError, match="2 decimal places"):
            parse_amount(raw)

    def test_limits(self) -> None:
        assert parse_amount(MAX_ABS_AMOUNT) == MAX_ABS_AMOUNT
        assert parse_amount(-MAX_ABS_AMOUNT) == -MAX_ABS_AMOUNT
        with pytest.raises(ValidationError, match="exceed"):
            parse_amount(MAX_ABS_AMOUNT + Decimal("0.01"))

    def test_negative_zero_is_normalised(self) -> None:
        assert str(parse_amount("-0")) == "0.00"
        assert str(Money.of("-0.00")) == "0.00 MAD"

    def test_error_names_field(self) -> None:
        with pytest.raises(ValidationError) as info:
            parse_amount("x", field="opening_balance")

        assert info.value.field == "opening_balance"


class TestMoney:
    def test_default_currency_is_mad(self) -> None:
        assert Money.of("1").currency == "MAD"

    def test_decimal_arithmetic_is_exact(self) -> None:
        assert 0.1 + 0.2 != 0.3  # the float problem this type exists to avoid
        assert Money.of("0.10") + Money.of("0.20") == Money.of("0.30")

    def test_many_small_amounts_sum_exactly(self) -> None:
        total = sum_money(Money.of("0.01") for _ in range(10_000))

        assert total == Money.of("100.00")

    def test_subtraction_and_negation(self) -> None:
        assert Money.of("300") - Money.of("500.50") == Money.of("-200.50")
        assert -Money.of("5") == Money.of("-5")
        assert abs(Money.of("-5")) == Money.of("5")

    @pytest.mark.parametrize(
        "value", ["0.01", "-0.01", "0", "12000.00", "999999999999.99", "-999999999999.99"]
    )
    def test_minor_units_round_trip(self, value: str) -> None:
        money = Money.of(value)

        assert isinstance(money.minor_units, int)
        assert Money.from_minor_units(money.minor_units) == money

    def test_minor_units_values(self) -> None:
        assert Money.of("12.34").minor_units == 1234
        assert Money.of("-0.05").minor_units == -5
        assert Money.from_minor_units(1_200_000) == Money.of("12000")

    @pytest.mark.parametrize("raw", [1.5, True, "100"])
    def test_from_minor_units_requires_int(self, raw: object) -> None:
        with pytest.raises(TypeError):
            Money.from_minor_units(raw)  # type: ignore[arg-type]

    def test_constructor_also_validates(self) -> None:
        with pytest.raises(ValidationError):
            Money(Decimal("0.001"))

    def test_computed_totals_may_exceed_the_input_limit(self) -> None:
        total = Money.of(MAX_ABS_AMOUNT) + Money.of(MAX_ABS_AMOUNT)

        assert total.amount == MAX_ABS_AMOUNT * 2
        with pytest.raises(ValidationError):
            Money.of(total.amount)  # still too large to enter directly

    def test_storable_limit(self) -> None:
        largest = Money(MAX_STORABLE_AMOUNT)

        assert largest.minor_units == 2**63 - 1
        with pytest.raises(ValidationError):
            _ = largest + Money.of("0.01")

    def test_mixing_currencies_is_rejected(self) -> None:
        mad, eur = Money.of("1", "MAD"), Money.of("1", "EUR")

        with pytest.raises(CurrencyMismatchError):
            _ = mad + eur
        with pytest.raises(CurrencyMismatchError):
            _ = mad - eur
        with pytest.raises(CurrencyMismatchError):
            _ = mad < eur
        assert mad != eur

    @pytest.mark.parametrize("code", ["mad", "MA", "MADD", "M4D", "", None])
    def test_invalid_currency(self, code: object) -> None:
        with pytest.raises(ValidationError):
            Money.of("1", code)  # type: ignore[arg-type]

    def test_ordering(self) -> None:
        assert Money.of("1") < Money.of("2")
        assert Money.of("2") >= Money.of("2.00")
        assert max(Money.of("3"), Money.of("-4")) == Money.of("3")

    def test_predicates(self) -> None:
        assert Money.zero().is_zero()
        assert Money.of("0.01").is_positive()
        assert Money.of("-0.01").is_negative()

    def test_formatting(self) -> None:
        assert str(Money.of("12000")) == "12,000.00 MAD"
        assert str(Money.of("-300.5")) == "-300.50 MAD"

    def test_is_immutable_and_hashable(self) -> None:
        money = Money.of("1")
        with pytest.raises(FrozenInstanceError):
            money.amount = Decimal("2")  # type: ignore[misc]
        assert {Money.of("1"), Money.of("1.00")} == {money}

    def test_not_equal_to_bare_numbers(self) -> None:
        assert Money.of("1") != Decimal("1")
        assert Money.of("1") != 1
