"""Automatic AI mode: local when ready, otherwise online (which still needs consent)."""

from collections.abc import Iterator

import pytest

from money_manager.ai.prompts import AIRequest
from money_manager.ai.providers import AnthropicProvider, OllamaProvider, create_provider
from money_manager.ai.secrets import ApiKey
from money_manager.ai.settings import MODE_LABELS, AIMode, AISettings, validate_settings
from money_manager.core.errors import AIUnavailableError, ConsentRequiredError
from tests.ai.support import TEST_KEY, OllamaStub, Recorder, client_factory, free_port


@pytest.fixture
def ollama() -> Iterator[OllamaStub]:
    stub = OllamaStub()
    yield stub
    stub.close()


def auto(url: str, model: str = "llama3.2") -> AISettings:
    return AISettings(AIMode.AUTO, local_url=url, local_model=model)


def test_automatic_is_offered_and_needs_no_mandatory_fields() -> None:
    assert "Automatic" in MODE_LABELS[AIMode.AUTO]
    assert validate_settings(AISettings(AIMode.AUTO)).mode is AIMode.AUTO


def test_local_model_is_preferred_when_running(ollama: OllamaStub) -> None:
    provider = create_provider(auto(ollama.url), ApiKey(TEST_KEY))
    assert isinstance(provider, OllamaProvider) and not provider.is_online
    assert provider.timeout_seconds == AISettings().timeout_seconds  # not the short probe


def test_falls_back_to_online_when_local_is_not_running() -> None:
    provider = create_provider(auto(f"http://127.0.0.1:{free_port()}"), ApiKey(TEST_KEY))
    assert isinstance(provider, AnthropicProvider) and provider.is_online


def test_falls_back_when_the_model_is_not_installed(ollama: OllamaStub) -> None:
    provider = create_provider(auto(ollama.url, "mistral"), ApiKey(TEST_KEY))
    assert isinstance(provider, AnthropicProvider)


def test_without_a_local_model_online_is_used() -> None:
    provider = create_provider(AISettings(AIMode.AUTO), ApiKey(TEST_KEY))
    assert isinstance(provider, AnthropicProvider)


def test_nothing_available() -> None:
    with pytest.raises(AIUnavailableError, match="Automatic mode found no AI"):
        create_provider(auto(f"http://127.0.0.1:{free_port()}"), None)


def test_online_fallback_still_requires_consent() -> None:
    recorder = Recorder()
    provider = create_provider(AISettings(AIMode.AUTO), ApiKey(TEST_KEY),
                               client_factory(recorder))
    with pytest.raises(ConsentRequiredError):
        provider.complete(AIRequest("system", "user"))
    assert recorder.requests == []
