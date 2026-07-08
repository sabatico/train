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
