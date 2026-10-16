"""Privacy notice and consent for sending data to an online provider.

An online provider never receives data silently: ``OnlineAIProvider`` refuses
to send unless it is given an ``OnlineConsent`` for exactly the payload it is
about to send. A consent can only be obtained by accepting a
``DataDisclosure``, which carries the warning and the complete text for the
user to review. If the data or the destination changes afterwards, the
consent no longer matches and the request is refused.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from money_manager.ai.context import NEVER_SENT
from money_manager.ai.prompts import AIRequest

_ISSUED_BY_DISCLOSURE = object()


@dataclass(frozen=True, slots=True)
class OnlineConsent:
    payload_digest: str
    destination: str
    granted_at: datetime
    _token: object = field(repr=False, compare=False, default=None)

    def __post_init__(self) -> None:
        if self._token is not _ISSUED_BY_DISCLOSURE:
            raise TypeError("Consent is only given by accepting a DataDisclosure.")

    def covers(self, request: AIRequest, destination: str) -> bool:
        return self.payload_digest == request.digest and self.destination == destination


@dataclass(frozen=True, slots=True)
class DataDisclosure:
    """What will be sent, where, and what never is."""

    provider: str
    destination: str  # host name, or "this computer"
    model: str
    is_online: bool
    request: AIRequest
    included: tuple[str, ...]
    never_sent: tuple[str, ...] = NEVER_SENT

    @property
    def requires_consent(self) -> bool:
        return self.is_online

    @property
    def title(self) -> str:
        if self.is_online:
            return f"Send financial information to {self.provider}?"
        return "Analyse with your local model"

    @property
    def warning(self) -> str:
        if not self.is_online:
            return (f"The summary below is processed by {self.model} running on this computer. "
                    "Nothing is sent over the internet.")
        return (f"Financial information about you will be sent over the internet to "
                f"{self.provider} ({self.destination}) to generate the answer. It leaves this "
                f"computer and is handled under {self.provider}'s terms and data-retention "
                "policy. Money Manager sends only the summary shown below, never your "
                "database.")

    def accept(self, now: datetime | None = None) -> OnlineConsent:
        """The user has reviewed this disclosure and agreed to send it."""
        return OnlineConsent(self.request.digest, self.destination,
                             now or datetime.now(UTC), _ISSUED_BY_DISCLOSURE)
