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
    assert b"grown-ups" in resp.data or b"dashboard" in resp.data


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
