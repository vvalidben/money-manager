"""The provider interface.

    AIProvider
    ├── LocalAIProvider   runs on this computer; data never leaves it
    │   └── OllamaProvider
    └── OnlineAIProvider  data leaves this computer; needs explicit consent
        └── AnthropicProvider

``complete()`` is the only way to send a request. It enforces the consent
rule for online providers, logs metadata only (never the prompt, the answer
or a key), and turns unexpected failures into ``AIResponseError`` so callers
only ever see ``AIError`` subclasses with messages safe to show.
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

from money_manager.ai.privacy import OnlineConsent
from money_manager.ai.prompts import AIRequest, AIResponse
from money_manager.core.errors import AIError, AIResponseError, ConsentRequiredError
from money_manager.core.i18n import tr

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ProviderStatus:
    available: bool
    message: str  # safe to show to the user
    models: tuple[str, ...] = ()  # models the provider offers, when known


class AIProvider(ABC):
    name: str  # display name, e.g. "Ollama"
    is_online: bool

    def __init__(self, model: str, timeout_seconds: int) -> None:
        self._model = model
        self._timeout = timeout_seconds

    @property
    def model(self) -> str:
        return self._model

    @property
    def timeout_seconds(self) -> int:
        return self._timeout

    @property
    @abstractmethod
    def destination(self) -> str:
        """Where the data goes: a host name, or "this computer"."""

    @abstractmethod
    def check_availability(self, *, probe: bool = False) -> ProviderStatus:
        """Whether a request could succeed now.

        With ``probe`` the provider may contact its service (without sending
        any financial data) to verify the connection, key and model.
        """

    @abstractmethod
    def _complete(self, request: AIRequest) -> AIResponse:
        """Send ``request``. Raise ``AIError`` subclasses for expected failures."""

    def complete(self, request: AIRequest, consent: OnlineConsent | None = None) -> AIResponse:
        self._check_consent(request, consent)
        started = time.monotonic()
        logger.info("AI request to %s (model %s, %d characters)", self.name, self.model,
                    len(request.payload_text))
        try:
            response = self._complete(request)
        except AIError as exc:
            logger.warning("AI request to %s failed: %s", self.name, type(exc).__name__)
            raise
        except Exception as exc:
            logger.error("Unexpected failure in the %s provider (%s)", self.name,
                         type(exc).__name__)
            raise AIResponseError(tr("{0} failed unexpectedly. Please try again.", self.name)) from exc
        logger.info("AI answer from %s in %.1f s (%d characters)", self.name,
                    time.monotonic() - started, len(response.text))
        return response

    def _check_consent(self, request: AIRequest, consent: OnlineConsent | None) -> None:
        if not self.is_online:
            return
        if consent is None:
            raise ConsentRequiredError(
                tr("Sending financial information to {0} needs your confirmation first.", self.name))
        if not consent.covers(request, self.destination):
            raise ConsentRequiredError(
                tr("The information to send changed after you agreed. Review it and confirm again."))


class LocalAIProvider(AIProvider, ABC):
    """A model on this computer: no consent needed, nothing crosses the network."""

    is_online = False

    @property
    def destination(self) -> str:
        return tr("this computer")


class OnlineAIProvider(AIProvider, ABC):
    """A remote service: every request needs a matching ``OnlineConsent``."""

    is_online = True
