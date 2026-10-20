"""Windows Hello (PIN, fingerprint or face) through the Windows Runtime.

``UserConsentVerifier`` asks Windows to confirm that the signed-in user is
present; Money Manager never sees the PIN or biometric data, only the answer.
The calls block, so the UI runs ``verify`` off the UI thread.

Tests and other platforms replace ``default_verifier`` with a fake.
"""

from __future__ import annotations

import asyncio
import ctypes
import logging
import sys
from enum import Enum
from typing import Protocol
from money_manager.core.i18n import tr

logger = logging.getLogger(__name__)

# The window Windows uses for the Hello prompt; a desktop app's prompt can open
# behind the app, so it is brought to the front once it appears.
PROMPT_WINDOW_CLASS = "Credential Dialog Xaml Host"
PROMPT_SEARCH_SECONDS = 4.0


class HelloStatus(Enum):
    AVAILABLE = "available"
    NOT_SET_UP = "not_set_up"  # no PIN / biometrics for this user, or turned off by policy
    UNSUPPORTED = "unsupported"  # not Windows, or the Windows Runtime is missing

    @property
    def explanation(self) -> str:
        return {
            "available": tr("Windows Hello is ready."),
            "not_set_up": tr("Windows Hello is not set up for your account. Add a PIN, fingerprint "
                          "or face in Windows Settings → Accounts → Sign-in options."),
            "unsupported": tr("Windows Hello is not available on this computer."),
        }[self.value]


class HelloResult(Enum):
    VERIFIED = "verified"
    CANCELED = "canceled"
    FAILED = "failed"  # wrong attempts, device busy …
    UNAVAILABLE = "unavailable"


class Verifier(Protocol):
    def status(self) -> HelloStatus: ...

    def verify(self, message: str) -> HelloResult: ...


class WindowsHello:
    """The real verifier (Windows 10/11 with the ``winrt`` packages)."""

    def status(self) -> HelloStatus:
        try:
            from winrt.windows.security.credentials.ui import (
                UserConsentVerifier,
                UserConsentVerifierAvailability,
            )

            availability = asyncio.run(UserConsentVerifier.check_availability_async())
        except Exception as exc:  # noqa: BLE001 - any failure means "cannot use it"
            logger.info("Windows Hello unavailable: %s", type(exc).__name__)
            return HelloStatus.UNSUPPORTED
        if availability == UserConsentVerifierAvailability.AVAILABLE:
            return HelloStatus.AVAILABLE
        if availability == UserConsentVerifierAvailability.DEVICE_NOT_PRESENT:
            return HelloStatus.UNSUPPORTED
        return HelloStatus.NOT_SET_UP

    def verify(self, message: str) -> HelloResult:
        try:
            from winrt.windows.security.credentials.ui import (
                UserConsentVerificationResult,
                UserConsentVerifier,
            )

            result = asyncio.run(_verify(UserConsentVerifier, message))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Windows Hello check failed: %s", type(exc).__name__)
            return HelloResult.UNAVAILABLE
        if result == UserConsentVerificationResult.VERIFIED:
            return HelloResult.VERIFIED
        if result == UserConsentVerificationResult.CANCELED:
            return HelloResult.CANCELED
        if result in (UserConsentVerificationResult.DEVICE_NOT_PRESENT,
                      UserConsentVerificationResult.NOT_CONFIGURED_FOR_USER,
                      UserConsentVerificationResult.DISABLED_BY_POLICY):
            return HelloResult.UNAVAILABLE
        return HelloResult.FAILED


async def _verify(verifier: object, message: str) -> object:
    request = asyncio.ensure_future(verifier.request_verification_async(message))  # type: ignore[attr-defined]
    await _bring_prompt_to_front(request)
    return await request


async def _bring_prompt_to_front(request: asyncio.Future[object]) -> None:
    if sys.platform != "win32":
        return
    user32 = ctypes.windll.user32
    waited = 0.0
    while not request.done() and waited < PROMPT_SEARCH_SECONDS:
        handle = user32.FindWindowW(PROMPT_WINDOW_CLASS, None)
        if handle:
            user32.SetForegroundWindow(handle)
            return
        await asyncio.sleep(0.1)
        waited += 0.1


def default_verifier() -> Verifier:
    return WindowsHello()
