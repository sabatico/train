"""Thin DeepSeek (OpenAI-compatible) chat client (ADR-012).

One module wraps the HTTP call so a provider swap is a base-URL + model change.
Uses stdlib urllib (no SDK dependency — CONVENTIONS: every dep is paid for).
Callers always wrap `chat()` in a try/except and fall back to the deterministic
engine on ANY failure (ADR-002): a slow or down API must never stall a 7-year-old.
Secrets come from the environment; nothing here logs the key or child PII.
"""
from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request

import certifi

# Explicit CA bundle — macOS Python.org builds ship without a system trust store,
# so the default context can't verify the provider's cert (ADR-012).
_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


class AgentError(Exception):
    """Any failure talking to the provider — signals the caller to fall back."""


def is_configured() -> bool:
    """True if an API key is present. When False, callers skip the agent entirely
    and use the engine fallback (e.g. in CI/tests, or before a key is set)."""
    return bool(os.environ.get("DEEPSEEK_API_KEY"))


def chat(
    messages: list[dict],
    *,
    tools: list[dict] | None = None,
    timeout: float = 10.0,
    temperature: float = 0.3,
    max_tokens: int = 512,
) -> dict:
    """One chat-completions call. Returns the raw provider response dict. Raises
    AgentError on any transport/HTTP/parse failure or if unconfigured."""
    if not is_configured():
        raise AgentError("DEEPSEEK_API_KEY not set")
    base = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
    payload: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if tools:
        payload["tools"] = tools
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ['DEEPSEEK_API_KEY']}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CONTEXT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        # never surface the raw error verbatim to callers/logs (could echo request
        # detail); a typed, message-scrubbed error is enough to trigger fallback.
        raise AgentError(f"agent call failed: {type(exc).__name__}") from None


def first_message(response: dict) -> dict:
    """The assistant message from a response, or {} if the shape is unexpected."""
    try:
        return response["choices"][0]["message"]
    except (KeyError, IndexError, TypeError):
        return {}
