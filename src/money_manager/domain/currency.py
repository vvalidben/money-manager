"""Supported currencies.

Money Manager keeps all amounts in one base currency and never converts
between currencies (there are no exchange rates). Every supported currency
has two decimal places, matching how ``Money`` stores minor units; adding a
currency is one entry in ``SUPPORTED_CURRENCIES``.
"""

from dataclasses import dataclass

from money_manager.core.errors import ValidationError
from money_manager.domain.money import DEFAULT_CURRENCY
from money_manager.core.i18n import tr


@dataclass(frozen=True, slots=True)
class CurrencyInfo:
    code: str  # ISO 4217
    name: str
    decimals: int = 2

    @property
    def label(self) -> str:
        return f"{self.code} – {tr(self.name)}"


SUPPORTED_CURRENCIES: dict[str, CurrencyInfo] = {
    info.code: info
    for info in (
        CurrencyInfo("MAD", "Moroccan dirham"),
        CurrencyInfo("EUR", "Euro"),
        CurrencyInfo("USD", "US dollar"),
        CurrencyInfo("GBP", "Pound sterling"),
        CurrencyInfo("CHF", "Swiss franc"),
        CurrencyInfo("CAD", "Canadian dollar"),
        CurrencyInfo("AED", "UAE dirham"),
        CurrencyInfo("SAR", "Saudi riyal"),
    )
}

assert DEFAULT_CURRENCY in SUPPORTED_CURRENCIES
assert all(info.decimals == 2 for info in SUPPORTED_CURRENCIES.values())


def validate_currency(code: object) -> str:
    text = code.strip().upper() if isinstance(code, str) else ""
    if text not in SUPPORTED_CURRENCIES:
        raise ValidationError(tr("Choose one of the supported currencies."), "currency")
    return text
