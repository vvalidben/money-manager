"""Provider configuration, API key handling and secret redaction."""

import logging
import pickle
import sys
import uuid

import pytest

from money_manager.ai.secrets import (
    ANTHROPIC_KEY_NAME,
    ApiKey,
    KeySource,
    MemorySecretStore,
    WindowsCredentialStore,
    resolve_key,
)
from money_manager.ai.settings import (
    DEFAULT_ONLINE_MODEL,
    AIMode,
    AISettings,
    validate_local_url,
    validate_settings,
)
from money_manager.core.errors import ValidationError
from money_manager.core.logging_setup import RedactingFormatter
from money_manager.core.redaction import REDACTED, redact_secrets

KEY = "sk-ant-api03-SECRETsecret0123456789"


class TestSettings:
    def test_ai_is_off_by_default(self) -> None:
        settings = AISettings()
        assert settings.mode is AIMode.OFF
        assert settings.online_model == DEFAULT_ONLINE_MODEL == "claude-opus-5"
        assert "key" not in " ".join(settings.to_dict())  # never a credential

    def test_round_trip(self) -> None:
        settings = AISettings(AIMode.LOCAL, "http://127.0.0.1:11434", "llama3.2", timeout_seconds=30)
        assert AISettings.from_dict(settings.to_dict()) == settings

    @pytest.mark.parametrize("data", [
        {"mode": "telepathy"}, {"timeout_seconds": "fast"}, {"local_url": "http://example.com"},
        {"mode": "local", "local_model": ""}, {"timeout_seconds": 10**6},
    ])
    def test_invalid_stored_values_fall_back_to_defaults(self, data: dict) -> None:
        assert AISettings.from_dict(data) == AISettings()

    @pytest.mark.parametrize("url", [
        "http://localhost:11434", "http://127.0.0.1:11434/", "http://[::1]:8080",
        "https://LOCALHOST", "http://127.8.9.10:1",
    ])
    def test_local_url_must_be_loopback(self, url: str) -> None:
        assert validate_local_url(url) == url.strip().rstrip("/")

    @pytest.mark.parametrize("url", [
        "http://192.168.1.20:11434", "http://example.com", "http://localhost.example.com",
        "ftp://localhost", "localhost:11434", "http://user:pw@localhost:11434",
        "http://localhost:11434/api", "http://localhost:99999", "http://10.0.0.1",
    ])
    def test_remote_or_malformed_local_urls_are_rejected(self, url: str) -> None:
        with pytest.raises(ValidationError) as info:
            validate_local_url(url)
        assert info.value.field == "local_url"

    @pytest.mark.parametrize(("changes", "field"), [
        ({"timeout_seconds": 4}, "timeout_seconds"),
        ({"timeout_seconds": 601}, "timeout_seconds"),
        ({"timeout_seconds": True}, "timeout_seconds"),
        ({"mode": AIMode.LOCAL, "local_model": " "}, "local_model"),
        ({"online_model": ""}, "online_model"),
        ({"online_model": "claude opus"}, "online_model"),
    ])
    def test_validation(self, changes: dict, field: str) -> None:
        with pytest.raises(ValidationError) as info:
            validate_settings(AISettings().with_changes(**changes))
        assert info.value.field == field

    def test_values_are_normalised(self) -> None:
        settings = validate_settings(AISettings(AIMode.LOCAL, " http://localhost:11434/ ",
                                                " llama3.2 "))
        assert (settings.local_url, settings.local_model) == ("http://localhost:11434",
                                                             "llama3.2")


class TestApiKey:
    def test_the_key_is_never_shown_by_accident(self) -> None:
        key = ApiKey(f"  {KEY} ")

        assert KEY not in repr(key) and KEY not in str(key) and KEY not in f"{key}"
        assert KEY not in repr([key]) and KEY not in repr({"key": key})
        assert key.reveal() == KEY
        assert key.hint == "…6789"

    def test_it_cannot_be_pickled(self) -> None:
        with pytest.raises(TypeError):
            pickle.dumps(ApiKey(KEY))

    @pytest.mark.parametrize("text", ["", "   ", "sk-ant with space", "x" * 513, "abc\x00"])
    def test_invalid_keys(self, text: str) -> None:
        with pytest.raises(ValidationError):
            ApiKey(text)

    def test_stored_key_wins_over_the_environment(self) -> None:
        store = MemorySecretStore()
        environ = {"ANTHROPIC_API_KEY": "sk-ant-from-environment-0000"}

        key, status = resolve_key(store, environ)
        assert status.source is KeySource.ENVIRONMENT and key is not None
        assert status.hint == "…0000"

        store.set(ANTHROPIC_KEY_NAME, KEY)
        key, status = resolve_key(store, environ)
        assert status.source is KeySource.STORED and key is not None and key.reveal() == KEY

    def test_no_key(self) -> None:
        key, status = resolve_key(MemorySecretStore(), {"ANTHROPIC_API_KEY": "  "})
        assert key is None and not status.available and status.hint == ""


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Credential Manager only")
def test_windows_credential_store_round_trip() -> None:
    store = WindowsCredentialStore(prefix=f"MoneyManagerTest-{uuid.uuid4()}/")
    try:
        assert store.get("key") is None
        store.set("key", KEY)
        assert store.get("key") == KEY
        store.set("key", "sk-ant-replaced-ü-0000")  # non-ASCII survives the UTF-16 blob
        assert store.get("key") == "sk-ant-replaced-ü-0000"
    finally:
        store.delete("key")
    assert store.get("key") is None
    store.delete("key")  # deleting twice is fine


class TestRedaction:
    @pytest.mark.parametrize("text", [
        f"Authorization: Bearer {KEY}", f"x-api-key: {KEY}", f'{{"api_key": "{KEY}"}}',
        f"request failed for key {KEY}", f"api_key={KEY}&x=1",
    ])
    def test_keys_are_removed(self, text: str) -> None:
        redacted = redact_secrets(text)
        assert KEY not in redacted and REDACTED in redacted

    def test_ordinary_text_is_kept(self) -> None:
        text = "Expenses increased by 18.0% (5,000.00 MAD -> 5,900.00 MAD)."
        assert redact_secrets(text) == text

    def test_log_lines_and_tracebacks_are_redacted(self) -> None:
        formatter = RedactingFormatter("%(message)s")
        try:
            raise RuntimeError(f"header x-api-key: {KEY}")
        except RuntimeError:
            record = logging.LogRecord("t", logging.ERROR, __file__, 1, "using %s", (KEY,),
                                       sys.exc_info())
        line = formatter.format(record)
        assert KEY not in line and "RuntimeError" in line
