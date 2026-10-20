"""Interface language: English (the source text), French and Arabic.

Every text shown to the user goes through ``tr``. English is written in the
code; other languages map each English text (a ``str.format`` template, with
``{0}``, ``{1}`` … for values) to its translation in ``core/locales``. A text
without a translation is shown in English, so a gap never breaks the app.

The language is chosen once at start-up, before the windows are built
(``set_language``); changing it in Settings asks for a restart.
"""

import logging
import sys
from collections.abc import Mapping

logger = logging.getLogger(__name__)

LANGUAGES = {"en": "English", "fr": "Français", "ar": "العربية"}
CHOICES = ("system", "en", "fr", "ar")
RIGHT_TO_LEFT = frozenset({"ar"})
# Languages that write amounts the French way (12 000,50) — Moroccan Arabic does too.
COMMA_DECIMALS = frozenset({"fr", "ar"})  # the setting; "system" follows Windows' display language
DEFAULT_CHOICE = "system"

_language = "en"
_catalog: Mapping[str, str] = {}


def set_language(code: str) -> str:
    """Use ``en``, ``fr`` or ``ar`` from now on (unknown codes fall back to English)."""
    global _language, _catalog
    if code == "fr":
        from money_manager.core.locales.fr import CATALOG

        _language, _catalog = "fr", CATALOG
    elif code == "ar":
        from money_manager.core.locales.ar import CATALOG as ARABIC

        _language, _catalog = "ar", ARABIC
    else:
        _language, _catalog = "en", {}
    logger.info("Interface language: %s", _language)
    return _language


def language() -> str:
    return _language


def is_right_to_left() -> bool:
    return _language in RIGHT_TO_LEFT


def comma_decimals() -> bool:
    return _language in COMMA_DECIMALS


def tr(text: str, *values: object) -> str:
    """``text`` in the interface language, with ``values`` filled into its ``{0}`` …"""
    translated = _catalog.get(text, text) if _catalog else text
    return translated.format(*values) if values else translated


def trc(context: str, text: str, *values: object) -> str:
    """Like ``tr``, for a text whose translation depends on where it is used (the
    catalog key is ``context|text``; without one, the plain translation is used)."""
    if _catalog and f"{context}|{text}" in _catalog:
        translated = _catalog[f"{context}|{text}"]
        return translated.format(*values) if values else translated
    return tr(text, *values)


def windows_language() -> str:
    """``fr`` or ``ar`` when Windows is displayed in French or Arabic, else ``en``."""
    if sys.platform != "win32":
        return "en"
    try:
        import ctypes

        primary = ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF
    except (OSError, AttributeError):
        return "en"
    return {0x0C: "fr", 0x01: "ar"}.get(primary, "en")  # LANG_FRENCH, LANG_ARABIC


def resolve_language(choice: str) -> str:
    if choice == "system":
        return windows_language()
    return choice if choice in LANGUAGES else "en"
