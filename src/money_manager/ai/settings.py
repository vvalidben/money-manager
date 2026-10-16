"""AI provider settings: what to use and where, never credentials.

AI is off until the user chooses a provider. The settings are stored in the
local database as JSON (see ``services.ai_service``); the API key is kept
separately in the operating system's credential store (``ai.secrets``).
"""

from collections.abc import Mapping
from dataclasses import dataclass, replace
from enum import StrEnum
from ipaddress import ip_address
from typing import Any, Self
from urllib.parse import urlsplit

from money_manager.core.errors import ValidationError

DEFAULT_LOCAL_URL = "http://localhost:11434"  # Ollama's default address
DEFAULT_ONLINE_MODEL = "claude-opus-5"
DEFAULT_TIMEOUT_SECONDS = 120
MIN_TIMEOUT_SECONDS = 5
MAX_TIMEOUT_SECONDS = 600
MAX_MODEL_NAME_LENGTH = 100

_LOOPBACK_NAMES = frozenset({"localhost"})


class AIMode(StrEnum):
    OFF = "off"
    LOCAL = "local"  # a model running on this computer (Ollama)
    ONLINE = "online"  # Anthropic's Claude API; data leaves this computer
    AUTO = "auto"  # local when available, otherwise online (still with consent)


MODE_LABELS = {
    AIMode.OFF: "Off",
    AIMode.LOCAL: "Local model (Ollama, on this computer)",
    AIMode.ONLINE: "Online (Anthropic Claude)",
    AIMode.AUTO: "Automatic (local when available, otherwise online)",
}


@dataclass(frozen=True, slots=True)
class AISettings:
    mode: AIMode = AIMode.OFF
    local_url: str = DEFAULT_LOCAL_URL
    local_model: str = ""  # chosen from the models installed in Ollama
    online_model: str = DEFAULT_ONLINE_MODEL
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS

    def with_changes(self, **changes: Any) -> Self:
        return replace(self, **changes)

    def to_dict(self) -> dict[str, Any]:
        return {"mode": self.mode.value, "local_url": self.local_url,
                "local_model": self.local_model, "online_model": self.online_model,
                "timeout_seconds": self.timeout_seconds}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        """Rebuild stored settings; unknown or invalid values fall back to the defaults."""
        defaults = cls()
        try:
            mode = AIMode(data.get("mode", defaults.mode))
        except ValueError:
            mode = defaults.mode
        timeout = data.get("timeout_seconds", defaults.timeout_seconds)
        candidate = cls(
            mode=mode,
            local_url=str(data.get("local_url", defaults.local_url)),
            local_model=str(data.get("local_model", defaults.local_model)),
            online_model=str(data.get("online_model", defaults.online_model)),
            timeout_seconds=timeout if isinstance(timeout, int) else defaults.timeout_seconds,
        )
        try:
            return validate_settings(candidate)
        except ValidationError:
            return defaults


def validate_settings(settings: AISettings, *, complete: bool = True) -> AISettings:
    """Check user-entered settings and return them normalised.

    ``complete=False`` allows a local mode without a chosen model, so the
    installed models can be listed before one is picked.
    """
    if not isinstance(settings.mode, AIMode):
        raise ValidationError("Choose how AI features should work.", "mode")
    if isinstance(settings.timeout_seconds, bool) or not isinstance(settings.timeout_seconds, int):
        raise ValidationError("Enter the timeout as a whole number of seconds.", "timeout_seconds")
    if not MIN_TIMEOUT_SECONDS <= settings.timeout_seconds <= MAX_TIMEOUT_SECONDS:
        raise ValidationError(
            f"The timeout must be between {MIN_TIMEOUT_SECONDS} and {MAX_TIMEOUT_SECONDS} "
            "seconds.", "timeout_seconds")
    local_model = _model_name(settings.local_model, "local_model", required=False)
    online_model = _model_name(settings.online_model, "online_model", required=True)
    local_url = validate_local_url(settings.local_url)
    if complete and settings.mode is AIMode.LOCAL and not local_model:
        raise ValidationError("Choose which local model to use.", "local_model")
    return replace(settings, local_url=local_url, local_model=local_model,
                   online_model=online_model)


def validate_local_url(url: str) -> str:
    """A local provider must be on this computer, so its address must be loopback.

    This keeps "local" honest: a mistyped or remote address would otherwise
    send financial data over the network without the online-provider warning.
    """
    text = url.strip().rstrip("/")
    parts = urlsplit(text)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ValidationError("Enter the local model address, e.g. http://localhost:11434.",
                              "local_url")
    if parts.username or parts.password or parts.query or parts.fragment or (
            parts.path not in {"", "/"}):
        raise ValidationError("Enter only the scheme, host and port of the local model.",
                              "local_url")
    if not is_loopback_host(parts.hostname):
        raise ValidationError(
            "A local model must run on this computer (localhost or 127.0.0.1). "
            "Use the online provider for remote services.", "local_url")
    try:
        parts.port  # noqa: B018 - validates the port number
    except ValueError as exc:
        raise ValidationError("The port number is not valid.", "local_url") from exc
    return text


def is_loopback_host(host: str) -> bool:
    host = host.strip("[]").lower()
    if host in _LOOPBACK_NAMES:
        return True
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False


def _model_name(value: str, field: str, *, required: bool) -> str:
    name = value.strip() if isinstance(value, str) else ""
    if required and not name:
        raise ValidationError("Enter a model name.", field)
    if len(name) > MAX_MODEL_NAME_LENGTH or any(c.isspace() or not c.isprintable() for c in name):
        raise ValidationError("The model name is not valid.", field)
    return name
