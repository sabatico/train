"""Tests for agent/client.py — the DeepSeek (OpenAI-compatible) HTTP wrapper
(ADR-012). Every network call is mocked: `urllib.request.urlopen` is
monkeypatched to a fake context manager so NOTHING here ever touches the
network. We assert both the parsed return values and the shape of the
`Request` object the module builds (URL, method, headers, body).
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest

from agent import client


# --------------------------------------------------------------- fakes
class _FakeResponse:
    """Stands in for the object returned by `urlopen(...).__enter__()`."""

    def __init__(self, payload: dict):
        self._body = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def _install_fake_urlopen(monkeypatch, payload: dict, captured: dict | None = None):
    """Monkeypatch urllib.request.urlopen to return a fake response and (if a
    `captured` dict is given) record the Request object it was called with."""

    def _fake_urlopen(req, timeout=None, context=None):
        if captured is not None:
            captured["request"] = req
            captured["timeout"] = timeout
            captured["context"] = context
        return _FakeResponse(payload)

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)


# --------------------------------------------------------------- is_configured
def test_is_configured_true_when_key_set(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key")
    assert client.is_configured() is True


def test_is_configured_false_when_key_absent(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    assert client.is_configured() is False


# --------------------------------------------------------------- chat: unconfigured
def test_chat_raises_agent_error_when_unconfigured(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(client.AgentError):
        client.chat([{"role": "user", "content": "hi"}])


# --------------------------------------------------------------- chat: success
def test_chat_success_returns_parsed_dict(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key")
    payload = {"choices": [{"message": {"role": "assistant", "content": "Great job!"}}]}
    _install_fake_urlopen(monkeypatch, payload)

    result = client.chat([{"role": "user", "content": "hi"}])
    assert result == payload


def test_chat_builds_request_with_correct_url_and_method(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key")
    monkeypatch.delenv("DEEPSEEK_BASE_URL", raising=False)
    captured: dict = {}
    _install_fake_urlopen(monkeypatch, {"choices": []}, captured)

    client.chat([{"role": "user", "content": "hi"}])

    req = captured["request"]
    assert isinstance(req, urllib.request.Request)
    assert req.full_url == "https://api.deepseek.com/chat/completions"
    assert req.get_method() == "POST"


def test_chat_builds_request_with_custom_base_url(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://example.test/v1/")
    captured: dict = {}
    _install_fake_urlopen(monkeypatch, {"choices": []}, captured)

    client.chat([{"role": "user", "content": "hi"}])

    req = captured["request"]
    # trailing slash on the base URL is stripped, no double-slash before the path
    assert req.full_url == "https://example.test/v1/chat/completions"


def test_chat_sends_authorization_bearer_header(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-super-secret")
    captured: dict = {}
    _install_fake_urlopen(monkeypatch, {"choices": []}, captured)

    client.chat([{"role": "user", "content": "hi"}])

    req = captured["request"]
    # urllib.request.Request lower-cases/capitalizes header keys internally;
    # get_header normalizes lookup for us.
    auth = req.get_header("Authorization")
    assert auth == "Bearer sk-super-secret"


def test_chat_body_includes_model_and_messages(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key")
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)
    captured: dict = {}
    _install_fake_urlopen(monkeypatch, {"choices": []}, captured)

    messages = [{"role": "user", "content": "spell 'love'"}]
    client.chat(messages)

    req = captured["request"]
    body = json.loads(req.data.decode("utf-8"))
    assert body["model"] == "deepseek-chat"
    assert body["messages"] == messages
    assert "tools" not in body  # no tools passed → key omitted


def test_chat_body_includes_tools_when_passed(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key")
    captured: dict = {}
    _install_fake_urlopen(monkeypatch, {"choices": []}, captured)

    tools = [{"type": "function", "function": {"name": "pick_exercise"}}]
    client.chat([{"role": "user", "content": "hi"}], tools=tools)

    req = captured["request"]
    body = json.loads(req.data.decode("utf-8"))
    assert body["tools"] == tools


def test_chat_uses_custom_model_env_var(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-reasoner")
    captured: dict = {}
    _install_fake_urlopen(monkeypatch, {"choices": []}, captured)

    client.chat([{"role": "user", "content": "hi"}])

    body = json.loads(captured["request"].data.decode("utf-8"))
    assert body["model"] == "deepseek-reasoner"


# --------------------------------------------------------------- chat: failures
def test_chat_raises_agent_error_on_url_error(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key")

    def _raise_url_error(req, timeout=None, context=None):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", _raise_url_error)

    with pytest.raises(client.AgentError):
        client.chat([{"role": "user", "content": "hi"}])


def test_chat_raises_agent_error_on_timeout(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key")

    def _raise_timeout(req, timeout=None, context=None):
        raise TimeoutError("timed out")

    monkeypatch.setattr(urllib.request, "urlopen", _raise_timeout)

    with pytest.raises(client.AgentError):
        client.chat([{"role": "user", "content": "hi"}])


def test_chat_raises_agent_error_on_invalid_json(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key")

    class _BadJsonResponse:
        def read(self):
            return b"not valid json {{{"

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

    def _fake_urlopen(req, timeout=None, context=None):
        return _BadJsonResponse()

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)

    with pytest.raises(client.AgentError):
        client.chat([{"role": "user", "content": "hi"}])


def test_chat_error_message_does_not_leak_key_or_request_detail(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-super-secret-value")

    def _raise_url_error(req, timeout=None, context=None):
        raise urllib.error.URLError("connection refused talking to sk-super-secret-value")

    monkeypatch.setattr(urllib.request, "urlopen", _raise_url_error)

    with pytest.raises(client.AgentError) as exc_info:
        client.chat([{"role": "user", "content": "hi"}])

    message = str(exc_info.value)
    assert "sk-super-secret-value" not in message
    # type-name only, e.g. "agent call failed: URLError"
    assert "URLError" in message
    assert "connection refused" not in message


def test_chat_unconfigured_error_message_does_not_leak_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(client.AgentError) as exc_info:
        client.chat([{"role": "user", "content": "hi"}])
    assert "DEEPSEEK_API_KEY" in str(exc_info.value)  # naming the missing var is fine
    # there is no key value to leak in this branch; just confirm it's short/typed
    assert "Bearer" not in str(exc_info.value)


# --------------------------------------------------------------- first_message
def test_first_message_returns_assistant_message():
    response = {
        "choices": [{"message": {"role": "assistant", "content": "Nice try!"}}]
    }
    assert client.first_message(response) == {"role": "assistant", "content": "Nice try!"}


def test_first_message_empty_dict_for_missing_choices():
    assert client.first_message({}) == {}


def test_first_message_empty_dict_for_empty_choices_list():
    assert client.first_message({"choices": []}) == {}


def test_first_message_empty_dict_for_none_response_shape():
    assert client.first_message({"choices": None}) == {}


def test_first_message_empty_dict_for_non_dict_choice():
    assert client.first_message({"choices": ["not-a-dict"]}) == {}
