"""Anthropic's Claude API through the official ``anthropic`` SDK.

The SDK is an optional dependency (``pip install money-manager[ai-online]``)
and is imported only when this provider is used. Every request needs an
``OnlineConsent`` (enforced by ``OnlineAIProvider``); the API key is passed
straight to the SDK client and never logged or stored by this module.
"""

import importlib.util
from collections.abc import Callable
from typing import Any

from money_manager.ai.prompts import AIRequest, AIResponse
from money_manager.ai.providers.base import OnlineAIProvider, ProviderStatus
from money_manager.ai.secrets import ANTHROPIC_KEY_ENV, ApiKey
from money_manager.core.errors import (
    AIAuthenticationError,
    AIError,
    AIRateLimitError,
    AIResponseError,
    AITimeoutError,
    AIUnavailableError,
)
from money_manager.core.redaction import redact_secrets

API_HOST = "api.anthropic.com"
MAX_RETRIES = 1  # timeouts are retried too, so the worst case is 2 × the timeout
# Server-side fallback when a model's safety classifier declines a request.
FALLBACK_BETA = "server-side-fallback-2026-07-01"
FALLBACK_MODELS = frozenset({"claude-opus-5", "claude-fable-5-1"})

ClientFactory = Callable[[ApiKey, int], Any]


def sdk_installed() -> bool:
    return importlib.util.find_spec("anthropic") is not None


def _default_client(key: ApiKey, timeout_seconds: int) -> Any:
    import anthropic

    return anthropic.Anthropic(api_key=key.reveal(), timeout=float(timeout_seconds),
                               max_retries=MAX_RETRIES)


class AnthropicProvider(OnlineAIProvider):
    name = "Anthropic"

    def __init__(self, api_key: ApiKey | None, model: str, timeout_seconds: int,
                 client_factory: ClientFactory | None = None) -> None:
        super().__init__(model, timeout_seconds)
        self._key = api_key
        self._client_factory = client_factory
        self._client: Any = None

    @property
    def destination(self) -> str:
        return API_HOST

    def _get_client(self) -> Any:
        if self._client_factory is None and not sdk_installed():
            raise AIUnavailableError(
                "The online provider needs the optional 'anthropic' package. Install it with "
                "pip install \"money-manager[ai-online]\".")
        if self._key is None:
            raise AIUnavailableError(
                f"No Anthropic API key. Add one in Settings or set {ANTHROPIC_KEY_ENV}.")
        if self._client is None:
            factory = self._client_factory or _default_client
            self._client = factory(self._key, self._timeout)
        return self._client

    # ----------------------------------------------------------- interface

    def check_availability(self, *, probe: bool = False) -> ProviderStatus:
        try:
            client = self._get_client()
            if probe:  # sends no financial data: only asks whether the model exists
                with self._mapped_errors():
                    client.models.retrieve(self.model)
        except AIError as exc:
            return ProviderStatus(False, str(exc))
        if probe:
            return ProviderStatus(True, f"Connected: {self.model} at {API_HOST}.")
        return ProviderStatus(True, f"Configured: {self.model} at {API_HOST} (not contacted).")

    def _complete(self, request: AIRequest) -> AIResponse:
        client = self._get_client()
        params: dict[str, Any] = {
            "model": self.model,
            "max_tokens": request.max_output_tokens,
            "system": request.system,
            "messages": [{"role": "user", "content": request.user}],
        }
        if self.model in FALLBACK_MODELS:
            params.update(betas=[FALLBACK_BETA], fallbacks="default")
        with self._mapped_errors(), client.beta.messages.stream(**params) as stream:
            message = stream.get_final_message()

        if message.stop_reason == "refusal":
            raise AIResponseError("The provider declined to answer this request.")
        text = "".join(block.text for block in message.content
                       if getattr(block, "type", None) == "text").strip()
        if not text:
            raise AIResponseError("The provider returned an empty answer.")
        return AIResponse(text=text, provider=self.name, model=str(message.model),
                          truncated=message.stop_reason == "max_tokens")

    def _mapped_errors(self) -> "_ErrorMapper":
        return _ErrorMapper(self.model, self._timeout)


class _ErrorMapper:
    """Translate SDK exceptions (most specific first) into safe application errors."""

    def __init__(self, model: str, timeout: int) -> None:
        self._model = model
        self._timeout = timeout

    def __enter__(self) -> None:
        return None

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None,
                 _tb: object) -> bool:
        if exc is None or isinstance(exc, AIError) or not sdk_installed():
            return False
        import anthropic

        mapped: AIError | None = None
        if isinstance(exc, anthropic.AuthenticationError):
            mapped = AIAuthenticationError("Anthropic rejected the API key. Check it in Settings.")
        elif isinstance(exc, anthropic.PermissionDeniedError):
            mapped = AIAuthenticationError("This API key is not allowed to use the model.")
        elif isinstance(exc, anthropic.NotFoundError):
            mapped = AIUnavailableError(f"The model '{self._model}' was not found at Anthropic.")
        elif isinstance(exc, anthropic.RateLimitError):
            mapped = AIRateLimitError("Anthropic is receiving too many requests. Try again in "
                                      "a minute.")
        elif isinstance(exc, anthropic.BadRequestError):
            mapped = AIResponseError("Anthropic could not process the request: "
                                     f"{redact_secrets(exc.message)}")
        elif isinstance(exc, anthropic.APIStatusError):
            mapped = AIResponseError(f"Anthropic had a problem (HTTP {exc.status_code}). "
                                     "Try again later.")
        elif isinstance(exc, anthropic.APITimeoutError):
            mapped = AITimeoutError(f"Anthropic did not answer within {self._timeout} seconds.")
        elif isinstance(exc, anthropic.APIConnectionError):
            mapped = AIUnavailableError(f"Could not reach {API_HOST}. Check the internet "
                                        "connection.")
        if mapped is None:
            return False
        raise mapped from exc
