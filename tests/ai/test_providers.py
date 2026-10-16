"""Provider interface, consent enforcement, Ollama (real local HTTP server) and
Anthropic (real SDK over a mock transport)."""

import logging
from collections.abc import Callable, Iterator
from datetime import datetime
from typing import Any

import pytest

from money_manager.ai.privacy import DataDisclosure, OnlineConsent
from money_manager.ai.prompts import AIRequest, AIResponse
from money_manager.ai.providers import (
    AIProvider,
    AnthropicProvider,
    LocalAIProvider,
    OllamaProvider,
    OnlineAIProvider,
    ProviderStatus,
    create_provider,
)
from money_manager.ai.providers.anthropic_provider import FALLBACK_BETA
from money_manager.ai.providers.ollama import is_cloud_model
from money_manager.ai.secrets import ApiKey
from money_manager.ai.settings import AIMode, AISettings
from money_manager.core.errors import (
    AIAuthenticationError,
    AIDisabledError,
    AIError,
    AIRateLimitError,
    AIResponseError,
    AITimeoutError,
    AIUnavailableError,
    ConsentRequiredError,
)
from tests.ai.support import (
    OllamaStub,
    free_port,
    TEST_KEY,
    Recorder,
    api_error,
    client_factory,
    httpx2,
    sse_answer,
)

REQUEST = AIRequest(system="Be factual.", user="<financial_analysis>Income: 12,000.00 MAD"
                                                "</financial_analysis>\n\nQuestion: Summarise.")


def disclosure_for(provider: AIProvider, request: AIRequest = REQUEST) -> DataDisclosure:
    return DataDisclosure(provider.name, provider.destination, provider.model,
                          provider.is_online, request, ("totals",))


# ------------------------------------------------------------ interface


class FakeOnline(OnlineAIProvider):
    name = "Fake online"

    def __init__(self, behaviour: Callable[[AIRequest], AIResponse] | None = None) -> None:
        super().__init__("fake-model", 30)
        self.sent: list[AIRequest] = []
        self._behaviour = behaviour

    @property
    def destination(self) -> str:
        return "ai.example.com"

    def check_availability(self, *, probe: bool = False) -> ProviderStatus:
        return ProviderStatus(True, "ok")

    def _complete(self, request: AIRequest) -> AIResponse:
        self.sent.append(request)
        if self._behaviour:
            return self._behaviour(request)
        return AIResponse("answer", self.name, self.model)


class FakeLocal(LocalAIProvider):
    name = "Fake local"

    def check_availability(self, *, probe: bool = False) -> ProviderStatus:
        return ProviderStatus(True, "ok")

    def _complete(self, request: AIRequest) -> AIResponse:
        return AIResponse("local answer", self.name, self.model)


class TestInterface:
    def test_hierarchy(self) -> None:
        assert issubclass(OllamaProvider, LocalAIProvider)
        assert issubclass(AnthropicProvider, OnlineAIProvider)
        assert issubclass(LocalAIProvider, AIProvider) and issubclass(OnlineAIProvider, AIProvider)
        assert not LocalAIProvider.is_online and OnlineAIProvider.is_online
        with pytest.raises(TypeError):
            AIProvider("m", 10)  # type: ignore[abstract]

    def test_online_provider_never_sends_without_consent(self) -> None:
        provider = FakeOnline()
        with pytest.raises(ConsentRequiredError):
            provider.complete(REQUEST)
        assert provider.sent == []

    def test_consent_covers_only_the_reviewed_payload(self) -> None:
        provider = FakeOnline()
        consent = disclosure_for(provider).accept()
        changed = AIRequest(REQUEST.system, REQUEST.user + " And more data.")

        with pytest.raises(ConsentRequiredError, match="changed"):
            provider.complete(changed, consent)
        assert provider.sent == []
        assert provider.complete(REQUEST, consent).text == "answer"
        assert provider.sent == [REQUEST]

    def test_consent_for_another_destination_is_refused(self) -> None:
        other = FakeOnline()
        other_destination = DataDisclosure("Other", "other.example.com", "m", True, REQUEST, ())
        with pytest.raises(ConsentRequiredError):
            other.complete(REQUEST, other_destination.accept())

    def test_consent_cannot_be_forged(self) -> None:
        with pytest.raises(TypeError):
            OnlineConsent(REQUEST.digest, "ai.example.com", datetime.now())

    def test_local_provider_needs_no_consent(self) -> None:
        provider = FakeLocal("small-model", 30)
        assert provider.destination == "this computer"
        assert provider.complete(REQUEST).text == "local answer"
        assert not disclosure_for(provider).requires_consent

    def test_unexpected_failures_become_safe_errors(self) -> None:
        def boom(request: AIRequest) -> AIResponse:
            raise KeyError("internal detail")

        provider = FakeOnline(boom)
        with pytest.raises(AIResponseError, match="failed unexpectedly") as info:
            provider.complete(REQUEST, disclosure_for(provider).accept())
        assert "internal detail" not in str(info.value)

    def test_logs_hold_metadata_only(self, caplog: pytest.LogCaptureFixture) -> None:
        provider = FakeOnline(lambda r: AIResponse("Cut dining out by 300 MAD", "Fake", "m"))
        with caplog.at_level(logging.DEBUG):
            provider.complete(REQUEST, disclosure_for(provider).accept())
        logged = caplog.text
        assert "Fake online" in logged and "characters" in logged
        for private in ("12,000.00", "Summarise", "Be factual", "dining"):
            assert private not in logged

    def test_factory(self) -> None:
        with pytest.raises(AIDisabledError):
            create_provider(AISettings(), None)
        local = create_provider(AISettings(AIMode.LOCAL, local_model="llama3.2"), None)
        online = create_provider(AISettings(AIMode.ONLINE), ApiKey(TEST_KEY))
        assert isinstance(local, OllamaProvider) and isinstance(online, AnthropicProvider)
        assert online.destination == "api.anthropic.com" and online.model == "claude-opus-5"


# --------------------------------------------------------------- Ollama


@pytest.fixture
def ollama() -> Iterator[OllamaStub]:
    stub = OllamaStub()
    yield stub
    stub.close()


class TestOllama:
    def test_answer_is_streamed_and_joined(self, ollama: OllamaStub) -> None:
        answer = OllamaProvider(ollama.url, "llama3.2", 10).complete(REQUEST)

        assert (answer.text, answer.model, answer.truncated) == ("Spending rose.", "llama3.2",
                                                                 False)
        path, body = ollama.requests[-1]
        assert path == "/api/chat" and body is not None
        assert body["model"] == "llama3.2" and body["stream"] is True
        assert body["messages"] == [{"role": "system", "content": REQUEST.system},
                                    {"role": "user", "content": REQUEST.user}]

    def test_output_limit(self, ollama: OllamaStub) -> None:
        ollama.chat_lines[-1]["done_reason"] = "length"
        assert OllamaProvider(ollama.url, "llama3.2", 10).complete(REQUEST).truncated

    def test_availability(self, ollama: OllamaStub) -> None:
        ollama.models.append({"name": "gpt-oss:120b-cloud"})
        ollama.models.append({"name": "mirror:latest", "remote_host": "https://ollama.com"})

        ready = OllamaProvider(ollama.url, "llama3.2", 10).check_availability()
        missing = OllamaProvider(ollama.url, "mistral", 10).check_availability()
        unset = OllamaProvider(ollama.url, "", 10).check_availability()

        assert ready.available and ready.models == ("llama3.2:latest",)  # cloud models hidden
        assert not missing.available and "ollama pull mistral" in missing.message
        assert not unset.available and unset.models == ("llama3.2:latest",)

    def test_no_models_installed(self, ollama: OllamaStub) -> None:
        ollama.models.clear()
        status = OllamaProvider(ollama.url, "llama3.2", 10).check_availability()
        assert not status.available and "no local model" in status.message

    def test_not_running(self) -> None:
        provider = OllamaProvider(f"http://127.0.0.1:{free_port()}", "llama3.2", 5)
        status = provider.check_availability()
        assert not status.available and "not running" in status.message
        with pytest.raises(AIUnavailableError, match="not running"):
            provider.complete(REQUEST)

    def test_timeout(self, ollama: OllamaStub) -> None:
        ollama.delay = 1.5
        with pytest.raises(AITimeoutError, match="1 seconds"):
            OllamaProvider(ollama.url, "llama3.2", 1).complete(REQUEST)

    @pytest.mark.parametrize(("status", "error"), [(404, AIUnavailableError),
                                                   (500, AIResponseError)])
    def test_http_errors(self, ollama: OllamaStub, status: int, error: type[AIError]) -> None:
        ollama.chat_status = status
        with pytest.raises(error):
            OllamaProvider(ollama.url, "llama3.2", 10).complete(REQUEST)

    def test_error_and_empty_streams(self, ollama: OllamaStub) -> None:
        provider = OllamaProvider(ollama.url, "llama3.2", 10)
        ollama.chat_lines = [{"error": "out of memory"}]
        with pytest.raises(AIResponseError, match="out of memory"):
            provider.complete(REQUEST)
        ollama.chat_lines = [{"done": True}]
        with pytest.raises(AIResponseError, match="empty"):
            provider.complete(REQUEST)
        ollama.chat_lines = [{"message": {"content": "half"}, "done": False}]
        with pytest.raises(AIResponseError, match="before finishing"):
            provider.complete(REQUEST)

    def test_system_proxies_are_ignored(self, ollama: OllamaStub,
                                        monkeypatch: pytest.MonkeyPatch) -> None:
        dead_proxy = f"http://127.0.0.1:{free_port()}"
        for name in ("HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy"):
            monkeypatch.setenv(name, dead_proxy)
        monkeypatch.delenv("NO_PROXY", raising=False)
        monkeypatch.delenv("no_proxy", raising=False)
        assert OllamaProvider(ollama.url, "llama3.2", 10).complete(REQUEST).text

    def test_cloud_models_are_refused_before_sending(self, ollama: OllamaStub) -> None:
        with pytest.raises(AIUnavailableError, match="Ollama's servers"):
            OllamaProvider(ollama.url, "gpt-oss:120b-cloud", 10).complete(REQUEST)
        assert ollama.requests == []

    @pytest.mark.parametrize(("name", "cloud"), [
        ("gpt-oss:120b-cloud", True), ("kimi:cloud", True), ("deepseek-v3.1:671b-cloud", True),
        ("llama3.2", False), ("llama3.2:3b", False), ("cloudy-model:7b", False),
    ])
    def test_cloud_model_names(self, name: str, cloud: bool) -> None:
        assert is_cloud_model(name) is cloud

    def test_remote_address_is_refused(self) -> None:
        with pytest.raises(AIUnavailableError, match="this computer"):
            OllamaProvider("http://192.168.1.10:11434", "llama3.2", 10)


# ------------------------------------------------------------ Anthropic


def claude(handler: Any, *, key: str | None = TEST_KEY, model: str = "claude-opus-5",
           timeout: int = 30) -> AnthropicProvider:
    return AnthropicProvider(None if key is None else ApiKey(key), model, timeout,
                             client_factory(handler))


def consented(provider: AnthropicProvider) -> OnlineConsent:
    return disclosure_for(provider).accept()


class TestAnthropic:
    def test_answer(self) -> None:
        recorder = Recorder()
        provider = claude(recorder)

        answer = provider.complete(REQUEST, consented(provider))

        assert (answer.text, answer.model, answer.truncated) == ("Your spending rose.",
                                                                 "claude-opus-5", False)
        [request] = recorder.requests
        assert request.url.host == "api.anthropic.com"
        assert request.headers["x-api-key"] == TEST_KEY
        assert request.headers["anthropic-beta"] == FALLBACK_BETA
        body = recorder.last_body
        assert body["model"] == "claude-opus-5" and body["fallbacks"] == "default"
        assert body["system"] == REQUEST.system
        assert body["messages"] == [{"role": "user", "content": REQUEST.user}]
        assert body["stream"] is True

    def test_other_models_are_sent_without_fallbacks(self) -> None:
        recorder = Recorder(lambda r: sse_answer(model="claude-sonnet-5"))
        provider = claude(recorder, model="claude-sonnet-5")
        provider.complete(REQUEST, consented(provider))
        assert "fallbacks" not in recorder.last_body
        assert "anthropic-beta" not in recorder.requests[0].headers

    def test_nothing_is_sent_without_consent(self) -> None:
        recorder = Recorder()
        with pytest.raises(ConsentRequiredError):
            claude(recorder).complete(REQUEST)
        assert recorder.requests == []

    def test_truncated_refused_and_empty_answers(self) -> None:
        provider = claude(Recorder(lambda r: sse_answer(stop_reason="max_tokens")))
        assert provider.complete(REQUEST, consented(provider)).truncated
        provider = claude(Recorder(lambda r: sse_answer("", stop_reason="refusal")))
        with pytest.raises(AIResponseError, match="declined"):
            provider.complete(REQUEST, consented(provider))
        provider = claude(Recorder(lambda r: sse_answer("   ")))
        with pytest.raises(AIResponseError, match="empty"):
            provider.complete(REQUEST, consented(provider))

    @pytest.mark.parametrize(("status", "error_type", "error"), [
        (401, "authentication_error", AIAuthenticationError),
        (403, "permission_error", AIAuthenticationError),
        (404, "not_found_error", AIUnavailableError),
        (429, "rate_limit_error", AIRateLimitError),
        (400, "invalid_request_error", AIResponseError),
        (500, "api_error", AIResponseError),
        (529, "overloaded_error", AIResponseError),
    ])
    def test_http_errors(self, status: int, error_type: str, error: type[AIError]) -> None:
        provider = claude(Recorder(api_error(status, error_type, f"bad {TEST_KEY}")))
        with pytest.raises(error) as info:
            provider.complete(REQUEST, consented(provider))
        assert TEST_KEY not in str(info.value)

    def test_timeout_and_network_errors(self) -> None:
        def timeout(request: Any) -> Any:
            raise httpx2.ReadTimeout("timed out", request=request)

        def offline(request: Any) -> Any:
            raise httpx2.ConnectError("no route", request=request)

        provider = claude(timeout, timeout=7)
        with pytest.raises(AITimeoutError, match="7 seconds"):
            provider.complete(REQUEST, consented(provider))
        provider = claude(offline)
        with pytest.raises(AIUnavailableError, match="internet"):
            provider.complete(REQUEST, consented(provider))

    def test_missing_key(self) -> None:
        recorder = Recorder()
        provider = claude(recorder, key=None)
        status = provider.check_availability()
        assert not status.available and "API key" in status.message
        with pytest.raises(AIUnavailableError, match="API key"):
            provider.complete(REQUEST, consented(provider))
        assert recorder.requests == []

    def test_availability_without_and_with_probe(self) -> None:
        recorder = Recorder(lambda r: httpx2.Response(200, json={
            "id": "claude-opus-5", "type": "model", "display_name": "Claude Opus 5",
            "created_at": "2026-01-01T00:00:00Z"}))
        provider = claude(recorder)

        quiet = provider.check_availability()
        assert quiet.available and "not contacted" in quiet.message
        assert recorder.requests == []  # no network without probe

        probed = provider.check_availability(probe=True)
        assert probed.available and "Connected" in probed.message
        [request] = recorder.requests
        assert request.method == "GET" and request.url.path == "/v1/models/claude-opus-5"
        assert request.content == b""  # a probe carries no financial data

    def test_probe_reports_a_rejected_key(self) -> None:
        provider = claude(Recorder(api_error(401, "authentication_error")))
        status = provider.check_availability(probe=True)
        assert not status.available and "rejected the API key" in status.message

    def test_missing_sdk(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from money_manager.ai.providers import anthropic_provider

        monkeypatch.setattr(anthropic_provider, "sdk_installed", lambda: False)
        provider = AnthropicProvider(ApiKey(TEST_KEY), "claude-opus-5", 30)
        status = provider.check_availability()
        assert not status.available and "money-manager[ai-online]" in status.message
