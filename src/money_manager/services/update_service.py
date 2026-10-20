"""Checking for a newer version (opt-in, off by default).

The only request is an HTTPS GET of the latest release on GitHub; it carries
no data about you or your finances (GitHub sees your IP address, as with any
web request). Nothing is downloaded or installed: when a newer version exists,
the app shows a link to its release page.
"""

import json
import logging
import re
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from money_manager import __version__
from money_manager.core.errors import MoneyManagerError
from money_manager.core.i18n import tr
from money_manager.services.settings_service import SettingsService

logger = logging.getLogger(__name__)

REPOSITORY = "vvalidben/money-manager"
LATEST_RELEASE_URL = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
RELEASES_PAGE = f"https://github.com/{REPOSITORY}/releases"
TIMEOUT_SECONDS = 10
MAX_RESPONSE_BYTES = 1024 * 1024

Fetch = Callable[[str], bytes]


class UpdateCheckError(MoneyManagerError):
    """The check could not be done (no connection, no release published …)."""


@dataclass(frozen=True, slots=True)
class UpdateInfo:
    latest: str
    current: str
    url: str

    @property
    def is_newer(self) -> bool:
        return version_key(self.latest) > version_key(self.current)


def version_key(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", text)[:3])


def fetch_url(url: str) -> bytes:
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"MoneyManager/{__version__}",
    })
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310
            return response.read(MAX_RESPONSE_BYTES)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise UpdateCheckError(tr("No published version was found.")) from exc
        raise UpdateCheckError(tr("The update server answered with an error ({0}).",
                                  exc.code)) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise UpdateCheckError(tr("Could not reach the update server. Are you online?")) from exc


class UpdateService:
    def __init__(self, settings: SettingsService, *, fetch: Fetch | None = None,
                 today: Callable[[], date] = date.today, current: str = __version__) -> None:
        self._settings = settings
        self._fetch = fetch
        self._today = today
        self._current = current

    def enabled(self) -> bool:
        return self._settings.update_check_enabled()

    def set_enabled(self, enabled: bool) -> bool:
        return self._settings.set_update_check_enabled(enabled)

    def due(self) -> bool:
        """Automatic check: switched on and not done today yet."""
        return self.enabled() and self._settings.last_update_check() != self._today()

    def check(self) -> UpdateInfo:
        """Ask GitHub for the latest release (blocking: call it off the UI thread)."""
        raw = (self._fetch or fetch_url)(LATEST_RELEASE_URL)  # looked up now, so tests can stub it
        try:
            document = json.loads(raw.decode("utf-8"))
            tag = str(document["tag_name"])
            url = str(document.get("html_url") or RELEASES_PAGE)
        except (ValueError, KeyError, TypeError) as exc:
            raise UpdateCheckError(tr("The update server sent an unexpected answer.")) from exc
        if not version_key(tag):
            raise UpdateCheckError(tr("The update server sent an unexpected answer."))
        if not url.startswith(f"https://github.com/{REPOSITORY}/"):
            url = RELEASES_PAGE  # only ever link to this project's own pages
        self._settings.set_last_update_check(self._today())
        info = UpdateInfo(tag.lstrip("vV"), self._current, url)
        logger.info("Update check: latest %s, this is %s", info.latest, info.current)
        return info
