"""Check an AI answer's numbers against the analysis it was given.

The AI must not calculate or invent figures. This check finds every amount
and percentage in the answer and reports those that do not appear in the
analysis text. Rounding is allowed: "about 24%" matches 23.5% and "12,000 MAD"
matches 12,000.00, but a new total the AI worked out itself is reported so
the user knows not to rely on it.

Plain small integers (counts such as "3 categories") and years are ignored.
"""

import re
from decimal import Decimal

_DATE = re.compile(r"\b\d{4}-\d{2}(?:-\d{2})?\b")
_NUMBER = re.compile(
    r"(?<![\w.,])[-+−]?(?P<int>\d{1,3}(?:,\d{3})+|\d+)(?:\.(?P<frac>\d+))?(?P<pct>\s?%)?")
_MAX_RELATIVE_ROUNDING = Decimal("0.05")


def _numbers(text: str) -> list[tuple[str, Decimal, int, bool]]:
    """(token, absolute value, decimals, is_percent) for each number outside dates."""
    found = []
    for match in _NUMBER.finditer(_DATE.sub(" ", text)):
        digits = match.group("int").replace(",", "")
        frac = match.group("frac") or ""
        value = Decimal(f"{digits}.{frac}" if frac else digits)
        found.append((match.group(0).strip(), value, len(frac), bool(match.group("pct"))))
    return found


def _tolerance(token: str, value: Decimal, decimals: int, is_percent: bool) -> Decimal:
    if decimals or is_percent:
        return Decimal(5) / Decimal(10) ** (decimals + 1)
    digits = token.replace(",", "").lstrip("+-−")
    zeros = len(digits) - len(digits.rstrip("0"))
    rounding = Decimal(5) * Decimal(10) ** (zeros - 1) if zeros else Decimal("0.5")
    return max(Decimal("0.5"), min(rounding, value * _MAX_RELATIVE_ROUNDING))


def _ignored(token: str, value: Decimal, decimals: int, is_percent: bool) -> bool:
    if is_percent or decimals or "," in token:
        return False
    return value < 100 or Decimal(1900) <= value <= Decimal(2100)


def unsupported_numbers(answer: str, analysis_text: str) -> tuple[str, ...]:
    """Numbers in ``answer`` that cannot be traced to ``analysis_text``."""
    known = _numbers(analysis_text)
    percents = [value for _, value, _, is_pct in known if is_pct]
    amounts = [value for _, value, _, is_pct in known if not is_pct]
    result: list[str] = []
    for token, value, decimals, is_percent in _numbers(answer):
        if _ignored(token, value, decimals, is_percent):
            continue
        tolerance = _tolerance(token, value, decimals, is_percent)
        candidates = percents if is_percent else amounts
        if not any(abs(value - known_value) <= tolerance for known_value in candidates):
            if token not in result:
                result.append(token)
    return tuple(result)
