"""Local models through Ollama's HTTP API (https://ollama.com).

Standard library only. The address must be loopback (``ai.settings``) and
system proxy settings are ignored, so requests cannot be routed off this
computer. Ollama can also run "cloud" models on Ollama's servers; those are
refused here because they would send data online without the online warning.
"""

import json
import socket
import urllib.error
import urllib.request
from collections.abc import Iterator
from typing import Any

from money_manager.ai.prompts import AIRequest, AIResponse
from money_manager.ai.providers.base import LocalAIProvider, ProviderStatus
from money_manager.ai.settings import validate_local_url
from money_manager.core.errors import (
    AIResponseError,
    AITimeoutError,
    AIUnavailableError,
    ValidationError,
)
from money_manager.core.i18n import tr

MAX_ERROR_BODY = 2000


def is_cloud_model(name: str, entry: dict[str, Any] | None = None) -> bool:
    """Ollama cloud models are tagged ``…-cloud`` / ``:cloud`` or list a remote host."""
    tag = name.rsplit(":", 1)[-1].lower() if ":" in name else ""
    if tag == "cloud" or tag.endswith("-cloud") or name.lower().endswith("-cloud"):
        return True
    return bool(entry and (entry.get("remote_host") or entry.get("remote_model")))


def _same_model(configured: str, installed: str) -> bool:
    """``llama3.2`` means ``llama3.2:latest``."""
    def full(name: str) -> str:
        return name if ":" in name else f"{name}:latest"
    return full(configured) == full(installed)


class OllamaProvider(LocalAIProvider):
    name = "Ollama"

    def __init__(self, base_url: str, model: str, timeout_seconds: int) -> None:
        super().__init__(model, timeout_seconds)
        try:
            self._base_url = validate_local_url(base_url)
        except ValidationError as exc:
            raise AIUnavailableError(str(exc)) from exc
        # An empty ProxyHandler disables HTTP(S)_PROXY for these requests.
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    # ------------------------------------------------------------ requests

    def _open(self, path: str, body: dict[str, Any] | None = None) -> Any:
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            self._base_url + path, data=data, method="GET" if body is None else "POST",
            headers={"Content-Type": "application/json"} if body is not None else {})
        try:
            return self._opener.open(request, timeout=self._timeout)
        except urllib.error.HTTPError as exc:
            raise self._http_error(exc) from exc
        except (TimeoutError, socket.timeout) as exc:
            raise self._timeout_error() from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, (TimeoutError, socket.timeout)):
                raise self._timeout_error() from exc
            raise AIUnavailableError(
                tr("Ollama is not running at {0}. Start Ollama and try again.", self._base_url)
            ) from exc

    def _timeout_error(self) -> AITimeoutError:
        return AITimeoutError(tr("Ollama did not answer within {0} seconds.", self._timeout))

    def _http_error(self, exc: urllib.error.HTTPError) -> Exception:
        try:
            detail = json.loads(exc.read(MAX_ERROR_BODY).decode("utf-8")).get("error", "")
        except (ValueError, OSError, AttributeError):
            detail = ""
        if exc.code == 404:
            return AIUnavailableError(
                tr("The model '{0}' is not installed in Ollama. Run 'ollama pull {1}' first.", self.model, self.model))
        suffix = f": {detail}" if isinstance(detail, str) and detail else ""
        return AIResponseError(tr("Ollama returned an error (HTTP {0}){1}.", exc.code, suffix))

    def installed_models(self) -> tuple[str, ...]:
        """Models installed locally; cloud models are left out."""
        with self._open("/api/tags") as response:
            try:
                payload = json.load(response)
            except ValueError as exc:
                raise AIResponseError(tr("Ollama sent an unreadable model list.")) from exc
        entries = payload.get("models", []) if isinstance(payload, dict) else []
        return tuple(sorted(
            str(entry["name"]) for entry in entries
            if isinstance(entry, dict) and "name" in entry
            and not is_cloud_model(str(entry["name"]), entry)))

    # ----------------------------------------------------------- interface

    def check_availability(self, *, probe: bool = False) -> ProviderStatus:
        try:
            models = self.installed_models()
        except (AIUnavailableError, AITimeoutError, AIResponseError) as exc:
            return ProviderStatus(False, str(exc))
        if not models:
            return ProviderStatus(False, "Ollama is running but no local model is installed. "
                                         "Install one with 'ollama pull <model>'.")
        if not self.model:
            return ProviderStatus(False, tr("Choose one of the installed models."), models)
        if is_cloud_model(self.model):
            return ProviderStatus(False, tr("This model runs on Ollama's servers, not on this "
                                         "computer. Choose a local model."), models)
        if not any(_same_model(self.model, installed) for installed in models):
            return ProviderStatus(False, tr("The model '{0}' is not installed. Run 'ollama pull {1}'.", self.model, self.model), models)
        return ProviderStatus(True, tr("Ready: {0} on this computer.", self.model), models)

    def _complete(self, request: AIRequest) -> AIResponse:
        if not self.model:
            raise AIUnavailableError(tr("Choose a local model in the settings first."))
        if is_cloud_model(self.model):
            raise AIUnavailableError(tr("This model runs on Ollama's servers, not on this "
                                     "computer. Choose a local model."))
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": request.system},
                         {"role": "user", "content": request.user}],
            "stream": True,  # the timeout then applies between chunks, not to the whole answer
            "options": {"num_predict": request.max_output_tokens},
        }
        parts: list[str] = []
        truncated = False
        with self._open("/api/chat", body) as response:
            for chunk in self._chunks(response):
                if "error" in chunk:
                    raise AIResponseError(tr("Ollama returned an error: {0}", chunk['error']))
                message = chunk.get("message")
                if isinstance(message, dict) and isinstance(message.get("content"), str):
                    parts.append(message["content"])
                if chunk.get("done"):
                    truncated = chunk.get("done_reason") == "length"
                    break
            else:
                raise AIResponseError(tr("Ollama stopped before finishing the answer."))
        text = "".join(parts).strip()
        if not text:
            raise AIResponseError(tr("Ollama returned an empty answer."))
        return AIResponse(text=text, provider=self.name, model=self.model, truncated=truncated)

    def _chunks(self, response: Any) -> Iterator[dict[str, Any]]:
        try:
            for line in response:
                line = line.strip()
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                except ValueError as exc:
                    raise AIResponseError(tr("Ollama sent an unreadable answer.")) from exc
                if isinstance(chunk, dict):
                    yield chunk
        except (TimeoutError, socket.timeout) as exc:
            raise self._timeout_error() from exc
