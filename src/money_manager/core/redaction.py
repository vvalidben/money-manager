"""Remove secrets from text before it is logged or shown.

A defence in depth: code never logs API keys on purpose, but exception
messages from third-party libraries could contain request headers.
"""

import re

REDACTED = "[REDACTED]"

_PATTERNS = (
    # Anthropic keys and similar prefixed tokens.
    re.compile(r"\bsk-[A-Za-z0-9][A-Za-z0-9_\-]{7,}"),
    # "api_key=...", "x-api-key: ...", "Authorization: Bearer ...", JSON or header style.
    re.compile(
        r"(?i)(\b(?:x-api-key|api[_-]?key|authorization|access[_-]?token)\b[\"']?\s*[:=]\s*[\"']?"
        r"(?:bearer\s+)?)[^\s\"',;}]+"
    ),
)


def redact_secrets(text: str) -> str:
    text = _PATTERNS[0].sub(REDACTED, text)
    return _PATTERNS[1].sub(lambda m: m.group(1) + REDACTED, text)
