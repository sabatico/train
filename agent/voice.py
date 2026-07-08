"""OpenAI TTS synthesis (ADR-013) — the single place that turns text into speech.

Shared by the build-time audio generator (`scripts/generate_audio.py`) and the
runtime read-aloud endpoint (`/api/tts`). Uses the steerable mini model with a
kid-friendly `instructions` prompt. Raises VoiceError on any failure so callers
fall back gracefully (browser TTS in the frontend). Never logs the key.
"""
from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request

import certifi

_SSL = ssl.create_default_context(cafile=certifi.where())

MODEL = os.environ.get("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
VOICE = os.environ.get("OPENAI_TTS_VOICE", "sage")
INSTRUCTIONS = os.environ.get(
    "OPENAI_TTS_INSTRUCTIONS",
    "very friendly and funny, kids communication oriented (for 6 y.o. girl auditory)",
)


class VoiceError(Exception):
    """Any failure synthesizing speech — signals the caller to fall back."""


def is_configured() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def synthesize(
    text: str,
    *,
    voice: str | None = None,
    instructions: str | None = None,
    model: str | None = None,
    timeout: float = 30.0,
) -> bytes:
    """Text → mp3 bytes via OpenAI TTS. Raises VoiceError if unconfigured or on
    any transport/HTTP failure."""
    if not is_configured():
        raise VoiceError("OPENAI_API_KEY not set")
    payload = {
        "model": model or MODEL,
        "voice": voice or VOICE,
        "input": text,
        "instructions": instructions or INSTRUCTIONS,
        "response_format": "mp3",
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/audio/speech",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL) as resp:
            return resp.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise VoiceError(f"tts failed: {type(exc).__name__}") from None
