"""Tests for app.py — the Flask skeleton (/healthz, /, /app, /parent).

app.py bootstraps the default student against engine.store at both import time
(module-level `app = create_app()`) and inside create_app() itself. To keep
these tests isolated from the real data/ dir, we monkeypatch store.DATA_ROOT /
store.WORD_BANK_DIR (via the data_root fixture) and then call create_app()
again ourselves -- create_app() is idempotent (bootstrap_student is idempotent)
so re-invoking it against the patched store is safe and gives us an app whose
bootstrap only ever touched the temp dir.
"""
from __future__ import annotations

import importlib

import pytest

from agent import voice


@pytest.fixture
def client(data_root):
    import app as app_module

    importlib.reload(app_module)  # re-run module body against patched store.DATA_ROOT
    flask_app = app_module.create_app()
    flask_app.testing = True
    with flask_app.test_client() as c:
        yield c


def test_healthz_status_ok(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert body["contract_version"] == 1
    assert "agent" in body


def test_healthz_content_type_is_json(client):
    resp = client.get("/healthz")
    assert resp.content_type.startswith("application/json")


def test_root_redirects_to_app(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/app")


def test_kid_app_route_ok(client):
    resp = client.get("/app")
    assert resp.status_code == 200
    assert b"Spell Quest" in resp.data


def test_parent_route_ok(client):
    resp = client.get("/parent")
    assert resp.status_code == 200
    # renders the dashboard (rose of winds), not the old placeholder
    assert b"rose of winds" in resp.data


def test_create_app_bootstraps_default_student(client, data_root):
    from engine import store

    # DEFAULT_STUDENT = "default" per app.py
    skills = store.load("default", "skills")
    assert len(skills["skills"]) == 14


def test_create_app_is_idempotent_across_calls(data_root):
    import app as app_module

    importlib.reload(app_module)
    app_module.create_app()
    app_module.create_app()  # must not raise, must not clobber

    from engine import store

    rewards = store.load("default", "rewards")
    assert rewards["stars_total"] == 0  # untouched defaults, no crash on repeat bootstrap


# ---------------------------------------------------------------------------
# GET /parent + POST /parent/settings (PAR-01/02/04)
# ---------------------------------------------------------------------------


def test_parent_route_contains_settings_form(client):
    resp = client.get("/parent")
    assert resp.status_code == 200
    assert b"rose of winds" in resp.data
    assert b'action="/parent/settings"' in resp.data
    assert b'name="items_per_session"' in resp.data
    assert b'name="tts_rate"' in resp.data


def test_parent_route_ok_on_fresh_student_no_sessions(client):
    # A freshly bootstrapped student has no session logs and no introduced-skill
    # errors yet — the dashboard must still render cleanly (empty states).
    resp = client.get("/parent")
    assert resp.status_code == 200
    assert b"No mistakes logged yet" in resp.data
    assert b"Work on next" in resp.data


def test_parent_settings_updates_and_redirects(client):
    resp = client.post(
        "/parent/settings",
        data={"items_per_session": "8", "tts_rate": "1.1"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/parent")

    from engine import store

    settings = store.load("default", "profile")["settings"]
    assert settings["items_per_session"] == 8
    assert settings["tts_rate"] == 1.1


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("99", 20),   # clamped to max
        ("1", 4),     # clamped to min
    ],
)
def test_parent_settings_clamps_items_per_session(client, raw, expected):
    resp = client.post(
        "/parent/settings",
        data={"items_per_session": raw, "tts_rate": "0.9"},
        follow_redirects=False,
    )
    assert resp.status_code == 302

    from engine import store

    settings = store.load("default", "profile")["settings"]
    assert settings["items_per_session"] == expected


def test_parent_settings_clamps_tts_rate_above_max(client):
    resp = client.post(
        "/parent/settings",
        data={"items_per_session": "10", "tts_rate": "9"},
        follow_redirects=False,
    )
    assert resp.status_code == 302

    from engine import store

    settings = store.load("default", "profile")["settings"]
    assert settings["tts_rate"] == 1.5


def test_parent_settings_ignores_non_numeric_input(client):
    from engine import store

    before = store.load("default", "profile")["settings"].copy()

    resp = client.post(
        "/parent/settings",
        data={"items_per_session": "not-a-number", "tts_rate": "also-bad"},
        follow_redirects=False,
    )
    assert resp.status_code == 302  # no crash, still redirects

    after = store.load("default", "profile")["settings"]
    assert after["items_per_session"] == before["items_per_session"]
    assert after["tts_rate"] == before["tts_rate"]


# ---------------------------------------------------------------------------
# POST /api/tts (ADR-013) — read-aloud, cached, mocked voice.synthesize.
#
# app.py does `from agent import voice` and calls `voice.synthesize(text)`, so
# we patch the `voice` attribute on the *reloaded* app module (same object as
# `agent.voice`, since importlib.reload(app_module) doesn't reload agent.voice
# itself -- but patching app_module.voice.synthesize is the most direct/robust
# target regardless).
# ---------------------------------------------------------------------------


def test_api_tts_empty_text_returns_400(client):
    resp = client.post("/api/tts", json={"text": ""})
    assert resp.status_code == 400


def test_api_tts_missing_text_returns_400(client):
    resp = client.post("/api/tts", json={})
    assert resp.status_code == 400


def test_api_tts_success_returns_audio_mpeg(client, monkeypatch):
    import app as app_module

    calls = []

    def _fake_synthesize(text, **kwargs):
        calls.append(text)
        return b"AUDIO"

    monkeypatch.setattr(app_module.voice, "synthesize", _fake_synthesize)

    resp = client.post("/api/tts", json={"text": "hello there"})
    assert resp.status_code == 200
    assert resp.content_type == "audio/mpeg"
    assert resp.data == b"AUDIO"
    assert len(calls) == 1


def test_api_tts_second_identical_request_is_served_from_cache(client, monkeypatch):
    import app as app_module
    from engine import store

    calls = []

    def _fake_synthesize(text, **kwargs):
        calls.append(text)
        return b"AUDIO"

    monkeypatch.setattr(app_module.voice, "synthesize", _fake_synthesize)

    first = client.post("/api/tts", json={"text": "hello there"})
    assert first.status_code == 200
    assert len(calls) == 1

    second = client.post("/api/tts", json={"text": "hello there"})
    assert second.status_code == 200
    assert second.data == b"AUDIO"
    # cache hit — voice.synthesize must NOT be called again
    assert len(calls) == 1

    cache_dir = store.DATA_ROOT / "tts_cache"
    assert cache_dir.is_dir()
    cached_files = list(cache_dir.glob("*.mp3"))
    assert len(cached_files) == 1


def test_api_tts_voice_error_returns_503(client, monkeypatch):
    import app as app_module

    def _raise_voice_error(text, **kwargs):
        raise voice.VoiceError("tts failed: URLError")

    monkeypatch.setattr(app_module.voice, "synthesize", _raise_voice_error)

    resp = client.post("/api/tts", json={"text": "a brand new uncached phrase"})
    assert resp.status_code == 503


def test_api_tts_long_text_is_truncated_and_still_succeeds(client, monkeypatch):
    import app as app_module

    captured = {}

    def _fake_synthesize(text, **kwargs):
        captured["text"] = text
        return b"AUDIO"

    monkeypatch.setattr(app_module.voice, "synthesize", _fake_synthesize)

    long_text = "a" * 1000
    resp = client.post("/api/tts", json={"text": long_text})
    assert resp.status_code == 200
    assert resp.data == b"AUDIO"
    assert len(captured["text"]) <= 400
