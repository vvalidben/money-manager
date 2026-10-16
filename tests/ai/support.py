"""Helpers for AI tests: a real ``anthropic`` client over a mock transport.

No request ever reaches the network; the handler sees exactly what the SDK
would send.
"""

import json
import socket
import threading
import time
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

anthropic = pytest.importorskip("anthropic")
httpx2 = pytest.importorskip("httpx2")

from money_manager.ai.prompts import AIRequest, AIResponse  # noqa: E402
from money_manager.ai.providers import AIProvider, ProviderStatus  # noqa: E402
from money_manager.ai.secrets import ApiKey  # noqa: E402

TEST_KEY = "sk-ant-test-0123456789abcdefWXYZ"

Handler = Callable[[Any], Any]


def sse_answer(text: str = "Your spending rose.", *, stop_reason: str = "end_turn",
               model: str = "claude-opus-5") -> Any:
    events = [
        {"type": "message_start", "message": {
            "id": "msg_test", "type": "message", "role": "assistant", "model": model,
            "content": [], "stop_reason": None, "stop_sequence": None,
            "usage": {"input_tokens": 10, "output_tokens": 1}}},
    ]
    if text:
        events += [
            {"type": "content_block_start", "index": 0,
             "content_block": {"type": "text", "text": ""}},
            {"type": "content_block_delta", "index": 0,
             "delta": {"type": "text_delta", "text": text}},
            {"type": "content_block_stop", "index": 0},
        ]
    events += [
        {"type": "message_delta", "delta": {"stop_reason": stop_reason, "stop_sequence": None},
         "usage": {"output_tokens": 5}},
        {"type": "message_stop"},
    ]
    body = "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events)
    return httpx2.Response(200, headers={"content-type": "text/event-stream"},
                           content=body.encode("utf-8"))


def api_error(status: int, error_type: str, message: str = "error") -> Any:
    return httpx2.Response(status, json={"type": "error",
                                         "error": {"type": error_type, "message": message}})


class Recorder:
    """A mock transport handler that records requests and replies with ``reply``."""

    def __init__(self, reply: Handler | Any = None) -> None:
        self.requests: list[Any] = []
        self._reply = reply if reply is not None else (lambda request: sse_answer())

    def __call__(self, request: Any) -> Any:
        self.requests.append(request)
        return self._reply(request) if callable(self._reply) else self._reply

    @property
    def last_body(self) -> dict[str, Any]:
        return json.loads(self.requests[-1].content)


def client_factory(handler: Handler) -> Callable[[ApiKey, int], Any]:
    def factory(key: ApiKey, timeout_seconds: int) -> Any:
        return anthropic.Anthropic(
            api_key=key.reveal(), timeout=float(timeout_seconds), max_retries=0,
            http_client=anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(handler)))
    return factory


class ScriptedProvider(AIProvider):
    """A provider with a fixed answer or error; records what it was sent.

    It inherits ``complete`` from ``AIProvider``, so the consent rule and error
    wrapping are the real ones.
    """

    def __init__(self, *, online: bool = False, reply: str = "Food spending rose by 22.0%.",
                 error: BaseException | None = None) -> None:
        super().__init__("test-model", 30)
        self.is_online = online
        self.name = "Anthropic" if online else "Ollama"
        self.reply = reply
        self.error = error
        self.sent: list[AIRequest] = []

    @property
    def destination(self) -> str:
        return "api.anthropic.com" if self.is_online else "this computer"

    def check_availability(self, *, probe: bool = False) -> ProviderStatus:
        return ProviderStatus(True, "ok")

    def _complete(self, request: AIRequest) -> AIResponse:
        self.sent.append(request)
        if self.error is not None:
            raise self.error
        return AIResponse(self.reply, self.name, self.model)


class OllamaStub:
    """A minimal Ollama API on 127.0.0.1 with scripted answers."""

    def __init__(self) -> None:
        self.models: list[dict[str, Any]] = [{"name": "llama3.2:latest"}]
        self.chat_status = 200
        self.chat_lines: list[dict[str, Any]] = [
            {"message": {"role": "assistant", "content": "Spending "}, "done": False},
            {"message": {"role": "assistant", "content": "rose."}, "done": False},
            {"done": True, "done_reason": "stop"},
        ]
        self.delay = 0.0
        self.requests: list[tuple[str, dict[str, Any] | None]] = []
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: Any) -> None:
                pass

            def _reply(self, status: int, body: bytes) -> None:
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self) -> None:
                stub.requests.append((self.path, None))
                self._reply(200, json.dumps({"models": stub.models}).encode())

            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", 0))
                stub.requests.append((self.path, json.loads(self.rfile.read(length))))
                time.sleep(stub.delay)
                if stub.chat_status != 200:
                    self._reply(stub.chat_status, b'{"error": "model \\"x\\" not found"}')
                    return
                body = b"".join(json.dumps(line).encode() + b"\n" for line in stub.chat_lines)
                self._reply(200, body)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]
