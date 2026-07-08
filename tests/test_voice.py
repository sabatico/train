"""Tests for agent/voice.py — the OpenAI TTS wrapper (ADR-013). Every network
call is mocked: `urllib.request.urlopen` is monkeypatched to a fake context
manager so NOTHING here ever touches the network. We assert both the returned
bytes and the shape of the `Request` object the module builds (URL, method,
headers, body).
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest

from agent import voice


# --------------------------------------------------------------- fakes
class _FakeResponse:
    """Stands in for the object returned by `urlopen(...).__enter__()`."""

    def __init__(self, body: bytes):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def _install_fake_urlopen(monkeypatch, body: bytes, captured: dict | None = None):
    """Monkeypatch urllib.request.urlopen to return a fake response and (if a
    `captured` dict is given) record the Request/timeout/context it was called
    with."""

    def _fake_urlopen(req, timeout=None, context=None):
        if captured is not None:
            captured["request"] = req
            captured["timeout"] = timeout
            captured["context"] = context
        return _FakeResponse(body)

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)


# --------------------------------------------------------------- is_configured
def test_is_configured_true_when_key_set(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    assert voice.is_configured() is True


def test_is_configured_false_when_key_absent(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert voice.is_configured() is False


# --------------------------------------------------------------- synthesize: unconfigured
def test_synthesize_raises_voice_error_when_unconfigured(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(voice.VoiceError):
        voice.synthesize("hi")


def test_synthesize_unconfigured_error_message_does_not_leak_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(voice.VoiceError) as exc_info:
        voice.synthesize("hi")
    # naming the missing var is fine; there's no key value to leak here
    assert "OPENAI_API_KEY" in str(exc_info.value)
    assert "Bearer" not in str(exc_info.value)


# --------------------------------------------------------------- synthesize: success
def test_synthesize_success_returns_mp3_bytes(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    _install_fake_urlopen(monkeypatch, b"MP3DATA")

    result = voice.synthesize("hi")
    assert result == b"MP3DATA"


def test_synthesize_builds_request_with_correct_url_and_method(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    captured: dict = {}
    _install_fake_urlopen(monkeypatch, b"MP3DATA", captured)

    voice.synthesize("hi")

    req = captured["request"]
    assert isinstance(req, urllib.request.Request)
    assert req.full_url == "https://api.openai.com/v1/audio/speech"
    assert req.get_method() == "POST"


def test_synthesize_sends_authorization_bearer_header(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-super-secret")
    captured: dict = {}
    _install_fake_urlopen(monkeypatch, b"MP3DATA", captured)

    voice.synthesize("hi")

    req = captured["request"]
    auth = req.get_header("Authorization")
    assert auth == "Bearer sk-super-secret"


def test_synthesize_body_includes_model_voice_input_instructions(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    captured: dict = {}
    _install_fake_urlopen(monkeypatch, b"MP3DATA", captured)

    voice.synthesize("hello there")

    req = captured["request"]
    body = json.loads(req.data.decode("utf-8"))
    assert body["model"] == voice.MODEL
    assert body["voice"] == voice.VOICE
    assert body["input"] == "hello there"
    assert body["instructions"] == voice.INSTRUCTIONS
    assert body["response_format"] == "mp3"


def test_synthesize_passes_timeout_and_ssl_context(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    captured: dict = {}
    _install_fake_urlopen(monkeypatch, b"MP3DATA", captured)

    voice.synthesize("hi", timeout=5.0)

    assert captured["timeout"] == 5.0
    assert captured["context"] is not None


# --------------------------------------------------------------- synthesize: overrides
def test_synthesize_voice_kwarg_overrides_default(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    captured: dict = {}
    _install_fake_urlopen(monkeypatch, b"MP3DATA", captured)

    voice.synthesize("hi", voice="alloy")

    body = json.loads(captured["request"].data.decode("utf-8"))
    assert body["voice"] == "alloy"


def test_synthesize_instructions_kwarg_overrides_default(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    captured: dict = {}
    _install_fake_urlopen(monkeypatch, b"MP3DATA", captured)

    voice.synthesize("hi", instructions="speak slowly")

    body = json.loads(captured["request"].data.decode("utf-8"))
    assert body["instructions"] == "speak slowly"


def test_synthesize_model_kwarg_overrides_default(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    captured: dict = {}
    _install_fake_urlopen(monkeypatch, b"MP3DATA", captured)

    voice.synthesize("hi", model="tts-1-hd")

    body = json.loads(captured["request"].data.decode("utf-8"))
    assert body["model"] == "tts-1-hd"


# --------------------------------------------------------------- synthesize: failures
def test_synthesize_raises_voice_error_on_url_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

    def _raise_url_error(req, timeout=None, context=None):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", _raise_url_error)

    with pytest.raises(voice.VoiceError):
        voice.synthesize("hi")


def test_synthesize_raises_voice_error_on_timeout(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

    def _raise_timeout(req, timeout=None, context=None):
        raise TimeoutError("timed out")

    monkeypatch.setattr(urllib.request, "urlopen", _raise_timeout)

    with pytest.raises(voice.VoiceError):
        voice.synthesize("hi")


def test_synthesize_error_message_does_not_leak_key_or_request_detail(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-super-secret-value")

    def _raise_url_error(req, timeout=None, context=None):
        raise urllib.error.URLError("connection refused talking to sk-super-secret-value")

    monkeypatch.setattr(urllib.request, "urlopen", _raise_url_error)

    with pytest.raises(voice.VoiceError) as exc_info:
        voice.synthesize("hi")

    message = str(exc_info.value)
    assert "sk-super-secret-value" not in message
    # type-name only, e.g. "tts failed: URLError"
    assert "URLError" in message
    assert "connection refused" not in message


def test_synthesize_timeout_error_message_does_not_leak_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-super-secret-value")

    def _raise_timeout(req, timeout=None, context=None):
        raise TimeoutError("timed out")

    monkeypatch.setattr(urllib.request, "urlopen", _raise_timeout)

    with pytest.raises(voice.VoiceError) as exc_info:
        voice.synthesize("hi")

    message = str(exc_info.value)
    assert "sk-super-secret-value" not in message
    assert "TimeoutError" in message
