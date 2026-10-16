"""Application exception hierarchy.

Expected failures raise a ``MoneyManagerError`` subclass whose message is safe
to show to the user. Anything else is treated as a bug: it is logged with a
full traceback and the user sees a generic message.
"""


class MoneyManagerError(Exception):
    """Base class for all expected, user-reportable application errors."""


class ConfigurationError(MoneyManagerError):
    """The application environment (folders, settings) is unusable."""


class DatabaseError(MoneyManagerError):
    """The local database could not be opened, created or updated."""


class ValidationError(MoneyManagerError):
    """Input was rejected. ``field`` names the offending input when known."""

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field


class InsufficientFundsError(ValidationError):
    """Moving or spending the amount would overdraw an allocation or Available."""


class NotFoundError(MoneyManagerError):
    """The requested record does not exist."""


class ConflictError(MoneyManagerError):
    """The operation clashes with existing data (duplicate name, record in use)."""


class CurrencyMismatchError(MoneyManagerError):
    """Amounts in different currencies were combined."""


class AIError(MoneyManagerError):
    """An optional AI feature failed. Messages never contain financial data or keys."""


class AIDisabledError(AIError):
    """AI features are switched off in the settings."""


class AIUnavailableError(AIError):
    """The configured provider cannot be used (not running, not installed, no key)."""


class AITimeoutError(AIError):
    """The provider did not answer within the configured time."""


class AIAuthenticationError(AIError):
    """The provider rejected the API key."""


class AIRateLimitError(AIError):
    """The provider asked to slow down; trying again later may work."""


class AIResponseError(AIError):
    """The provider answered with an error or with nothing usable."""


class ConsentRequiredError(AIError):
    """Data would leave this computer without the user's explicit consent."""
