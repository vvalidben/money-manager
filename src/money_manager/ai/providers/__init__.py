"""AI providers and the factory that builds one from the settings."""

import logging

from money_manager.ai.providers.anthropic_provider import AnthropicProvider, ClientFactory
from money_manager.ai.providers.base import (
    AIProvider,
    LocalAIProvider,
    OnlineAIProvider,
    ProviderStatus,
)
from money_manager.ai.providers.ollama import OllamaProvider
from money_manager.ai.secrets import ApiKey
from money_manager.ai.settings import AIMode, AISettings
from money_manager.core.errors import AIDisabledError, AIUnavailableError

logger = logging.getLogger(__name__)

AUTO_PROBE_TIMEOUT_SECONDS = 3  # how long automatic mode waits for the local model


def create_provider(settings: AISettings, api_key: ApiKey | None,
                    anthropic_client_factory: ClientFactory | None = None) -> AIProvider:
    match settings.mode:
        case AIMode.LOCAL:
            return OllamaProvider(settings.local_url, settings.local_model,
                                  settings.timeout_seconds)
        case AIMode.ONLINE:
            return AnthropicProvider(api_key, settings.online_model, settings.timeout_seconds,
                                     anthropic_client_factory)
        case AIMode.AUTO:
            return _automatic(settings, api_key, anthropic_client_factory)
        case _:
            raise AIDisabledError("AI features are turned off. Choose a provider in Settings.")


def _automatic(settings: AISettings, api_key: ApiKey | None,
               anthropic_client_factory: ClientFactory | None) -> AIProvider:
    """Local when the local model is ready, otherwise online.

    Choosing the online provider never sends anything by itself: every online
    request still needs the user's explicit consent.
    """
    if settings.local_model:
        probe = OllamaProvider(settings.local_url, settings.local_model,
                               min(AUTO_PROBE_TIMEOUT_SECONDS, settings.timeout_seconds))
        if probe.check_availability().available:
            logger.info("Automatic AI mode chose the local model")
            return OllamaProvider(settings.local_url, settings.local_model,
                                  settings.timeout_seconds)
    if api_key is not None:
        logger.info("Automatic AI mode chose the online provider")
        return AnthropicProvider(api_key, settings.online_model, settings.timeout_seconds,
                                 anthropic_client_factory)
    raise AIUnavailableError(
        "Automatic mode found no AI to use: start Ollama with the chosen local model, or add "
        "an Anthropic API key in Settings.")


__all__ = [
    "AIProvider",
    "AnthropicProvider",
    "LocalAIProvider",
    "OllamaProvider",
    "OnlineAIProvider",
    "ProviderStatus",
    "create_provider",
]
