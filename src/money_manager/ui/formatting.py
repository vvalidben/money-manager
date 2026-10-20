"""Display formatting for money, dates and transaction types (presentation only).

English: ``12,000.50 MAD``, ``38.2%``, ``05 Mar 2026``. French: ``12 000,50 MAD``,
``38,2 %``, ``05 mars 2026`` (no-break spaces, so a figure never wraps). The
language is read on every call, so nothing depends on when a module was imported.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from money_manager.core.i18n import language, tr
from money_manager.domain.enums import TransactionType
from money_manager.domain.money import Money

MINUS_SIGN = "−"
NO_BREAK_SPACE = "\u00a0"
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

TYPE_LABELS = {  # English; shown through tr()
    TransactionType.INCOME: "Income",
    TransactionType.EXPENSE: "Expense",
    TransactionType.ADJUSTMENT_IN: "Adjustment (+)",
    TransactionType.ADJUSTMENT_OUT: "Adjustment (−)",
}


def _month(number: int) -> str:
    return tr(_MONTHS[number - 1])


def _localise(text: str) -> str:
    """English digits (``12,000.5``) in the interface language's style."""
    if language() == "fr":
        return text.replace(",", NO_BREAK_SPACE).replace(".", ",")
    return text


def format_amount(amount: Decimal) -> str:
    """``12,000.00`` (``12 000,00`` in French), no currency."""
    return _localise(f"{amount:,.2f}")


def format_money(money: Money) -> str:
    """``12,000.00 MAD``; negative values use a real minus sign."""
    sign = MINUS_SIGN if money.is_negative() else ""
    space = NO_BREAK_SPACE if language() == "fr" else " "
    return f"{sign}{format_amount(abs(money.amount))}{space}{money.currency}"


def format_signed_money(money: Money) -> str:
    """Like ``format_money`` but always shows ``+`` for positive values."""
    return ("+" if money.is_positive() else "") + format_money(money)


def format_date(value: date) -> str:
    """Locale-independent ``05 Mar 2026``."""
    return f"{value.day:02d} {_month(value.month)} {value.year}"


def format_month(value: date) -> str:
    """``Mar 2026``."""
    return f"{_month(value.month)} {value.year}"


def month_abbreviation(value: date) -> str:
    return _month(value.month)


def format_day_range(start: date, end: date) -> str:
    """``1–27 Sep`` within a month, ``28 Aug – 3 Sep`` across months."""
    if (start.year, start.month) == (end.year, end.month):
        return f"{start.day}–{end.day} {_month(end.month)}"
    return f"{start.day} {_month(start.month)} – {end.day} {_month(end.month)}"


def format_percent(fraction: Decimal, *, signed: bool = False) -> str:
    """A fraction (0.3817) as ``38.2%``; ``signed`` adds ``+`` to positive values."""
    percent = (fraction * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    sign = MINUS_SIGN if percent < 0 else ("+" if signed and percent > 0 else "")
    if language() == "fr":
        return f"{sign}{_localise(str(abs(percent)))}{NO_BREAK_SPACE}%"
    return f"{sign}{abs(percent)}%"


def format_compact_amount(value: Decimal) -> str:
    """Axis-tick style: ``950``, ``12k``, ``1.5M`` (no currency)."""
    sign = MINUS_SIGN if value < 0 else ""
    magnitude = abs(value)
    for threshold, suffix in ((Decimal(1_000_000), "M"), (Decimal(1_000), "k")):
        if magnitude >= threshold:
            scaled = (magnitude / threshold).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
            text = f"{scaled:f}".rstrip("0").rstrip(".")
            return f"{sign}{_localise(text)}{suffix}"
    return f"{sign}{magnitude.quantize(Decimal(1), rounding=ROUND_HALF_UP)}"


def type_label(transaction_type: TransactionType) -> str:
    return tr(TYPE_LABELS[transaction_type])
