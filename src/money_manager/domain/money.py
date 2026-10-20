"""Exact monetary amounts.

``Money`` is a ``Decimal`` with exactly two fractional digits plus an ISO 4217
currency code. Floats are rejected outright: 0.1 has no exact binary
representation, and accepting floats would let rounding errors leak into
balances. Values with more than two decimal places are rejected rather than
rounded, so an amount is never silently changed.

The database stores the integer number of minor units (centimes for MAD).
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from functools import total_ordering
from typing import Self

from money_manager.core.errors import CurrencyMismatchError, ValidationError
from money_manager.core.i18n import language, tr

DEFAULT_CURRENCY = "MAD"
MINOR_UNIT_DIGITS = 2
# Largest single amount a user may enter (opening balance, transaction, ...).
MAX_ABS_AMOUNT = Decimal("999999999999.99")
# Largest value any Money may hold, e.g. a computed total: the most minor
# units a signed 64-bit SQLite INTEGER can store.
MAX_STORABLE_AMOUNT = Decimal(2**63 - 1).scaleb(-MINOR_UNIT_DIGITS)

_QUANTUM = Decimal(1).scaleb(-MINOR_UNIT_DIGITS)

AmountInput = Decimal | int | str


def parse_amount(
    value: object, field: str = "amount", limit: Decimal = MAX_ABS_AMOUNT
) -> Decimal:
    """Convert input into an exact two-decimal ``Decimal``.

    Accepts ``Decimal``, ``int`` and numeric strings. Rejects floats, bools,
    non-finite values, more than two decimal places and values above ``limit``.
    """
    if isinstance(value, bool):
        raise ValidationError(tr("Amount must be a number."), field)
    if isinstance(value, float):
        raise ValidationError(
            tr("Amounts must not be floats; use a Decimal or a string such as '12.50'."), field
        )
    if isinstance(value, Decimal):
        amount = value
    elif isinstance(value, int):
        amount = Decimal(value)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValidationError(tr("Enter an amount."), field)
        try:
            amount = Decimal(text)
        except InvalidOperation:
            raise ValidationError(tr("{0!r} is not a valid amount.", value), field) from None
    else:
        raise ValidationError(tr("Unsupported amount type: {0}.", type(value).__name__), field)

    if not amount.is_finite():
        raise ValidationError(tr("Amount must be a finite number."), field)
    if abs(amount) > limit:
        raise ValidationError(tr("Amount must not exceed {0:,} in size.", limit), field)
    quantized = amount.quantize(_QUANTUM)
    if quantized != amount:
        raise ValidationError(
            tr("Amount can have at most {0} decimal places.", MINOR_UNIT_DIGITS), field
        )
    # Normalise -0.00 so it never displays as a negative amount.
    return quantized.copy_abs() if quantized.is_zero() else quantized


_GROUPING_SPACES = str.maketrans("", "", "   ")
_TYPED_AMOUNT = re.compile(r"[+-]?(\d+(\.\d*)?|\.\d+)")


def parse_amount_text(text: object, field: str = "amount") -> Decimal:
    """Parse an amount typed by a person, e.g. ``1 200,50``, ``1200.5`` or ``-300``.

    Spaces group thousands; either a comma or a dot is the decimal separator.
    A separator followed by exactly three digits (``1,200`` / ``1.200``) is
    rejected as ambiguous instead of guessing between thousands and decimals.
    """
    if not isinstance(text, str):
        raise ValidationError(tr("Enter an amount."), field)
    compact = text.strip().translate(_GROUPING_SPACES)
    if not compact:
        raise ValidationError(tr("Enter an amount."), field)
    if "," in compact and "." in compact:
        raise ValidationError(
            tr("Use either a comma or a dot for decimals, and spaces to group thousands."), field
        )
    if compact.count(",") + compact.count(".") > 1:
        raise ValidationError(tr("Group thousands with spaces, e.g. 1 200 000."), field)
    compact = compact.replace(",", ".")
    _, separator, decimals = compact.partition(".")
    if separator and len(decimals) == 3 and decimals.isdigit():
        raise ValidationError(
            tr("'{0}' is ambiguous: write 1200 or 1 200 for thousands, or 1.20 for "
               "decimals.", text.strip()),
            field,
        )
    if not _TYPED_AMOUNT.fullmatch(compact):
        raise ValidationError(tr("'{0}' is not a valid amount.", text.strip()), field)
    return parse_amount(compact, field)


def validate_currency(code: object) -> str:
    if not (
        isinstance(code, str)
        and len(code) == 3
        and code.isascii()
        and code.isalpha()
        and code.isupper()
    ):
        raise ValidationError(
            tr("Currency must be a three-letter ISO 4217 code such as 'MAD'."), "currency"
        )
    return code


@total_ordering
@dataclass(frozen=True, slots=True)
class Money:
    """Immutable exact amount of money.

    ``Money.of`` is for user input and enforces ``MAX_ABS_AMOUNT``; the
    constructor (used for computed values) only enforces what can be stored.
    """

    amount: Decimal
    currency: str = DEFAULT_CURRENCY

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "amount", parse_amount(self.amount, limit=MAX_STORABLE_AMOUNT)
        )
        validate_currency(self.currency)

    @classmethod
    def of(cls, value: AmountInput, currency: str = DEFAULT_CURRENCY) -> Self:
        return cls(parse_amount(value), currency)

    @classmethod
    def zero(cls, currency: str = DEFAULT_CURRENCY) -> Self:
        return cls(Decimal(0), currency)

    @classmethod
    def from_minor_units(cls, minor_units: int, currency: str = DEFAULT_CURRENCY) -> Self:
        if isinstance(minor_units, bool) or not isinstance(minor_units, int):
            raise TypeError("minor_units must be an int")
        return cls(Decimal(minor_units).scaleb(-MINOR_UNIT_DIGITS), currency)

    @property
    def minor_units(self) -> int:
        return int(self.amount.scaleb(MINOR_UNIT_DIGITS))

    def is_zero(self) -> bool:
        return self.amount.is_zero()

    def is_positive(self) -> bool:
        return self.amount > 0

    def is_negative(self) -> bool:
        return self.amount < 0

    def __add__(self, other: object) -> "Money":
        if not isinstance(other, Money):
            return NotImplemented
        self._require_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: object) -> "Money":
        if not isinstance(other, Money):
            return NotImplemented
        self._require_same_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def __neg__(self) -> "Money":
        return Money(-self.amount, self.currency)

    def __abs__(self) -> "Money":
        return Money(abs(self.amount), self.currency)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._require_same_currency(other)
        return self.amount < other.amount

    def __str__(self) -> str:
        text = f"{self.amount:,.2f}"
        if language() == "fr":  # 12 000,50 MAD
            text = text.replace(",", " ").replace(".", ",")
        return f"{text} {self.currency}"

    def _require_same_currency(self, other: "Money") -> None:
        if other.currency != self.currency:
            raise CurrencyMismatchError(
                tr("Cannot combine {0} and {1} amounts.", self.currency, other.currency)
            )


def sum_money(values: Iterable[Money], currency: str = DEFAULT_CURRENCY) -> Money:
    total = Money.zero(currency)
    for value in values:
        total = total + value
    return total
