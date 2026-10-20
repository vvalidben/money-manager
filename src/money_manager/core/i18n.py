"""Interface language: English (the source text) and French.

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

LANGUAGES = {"en": "English", "fr": "Français"}
CHOICES = ("system", "en", "fr")  # the setting; "system" follows Windows' display language
DEFAULT_CHOICE = "system"

_language = "en"
_catalog: Mapping[str, str] = {}


def set_language(code: str) -> str:
    """Use ``en`` or ``fr`` from now on (unknown codes fall back to English)."""
    global _language, _catalog
    if code == "fr":
        from money_manager.core.locales.fr import CATALOG

        _language, _catalog = "fr", CATALOG
    else:
        _language, _catalog = "en", {}
    logger.info("Interface language: %s", _language)
    return _language


def language() -> str:
    return _language


def tr(text: str, *values: object) -> str:
    """``text`` in the interface language, with ``values`` filled into its ``{0}`` …"""
    translated = _catalog.get(text, text) if _catalog else text
    return translated.format(*values) if values else translated


def windows_language() -> str:
    """``fr`` when Windows is displayed in French, else ``en``."""
    if sys.platform != "win32":
        return "en"
    try:
        import ctypes

        primary = ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF
    except (OSError, AttributeError):
        return "en"
    return "fr" if primary == 0x0C else "en"  # LANG_FRENCH


def resolve_language(choice: str) -> str:
    if choice == "system":
        return windows_language()
    return choice if choice in LANGUAGES else "en"
