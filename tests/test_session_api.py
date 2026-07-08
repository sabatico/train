"""Tests for the /api/session/* and /api/skills routes in app.py (ADR-009).

Follows the same isolation pattern as tests/test_app.py: monkeypatch
store.DATA_ROOT/WORD_BANK_DIR (via the data_root fixture) then reload app.py
and call create_app() again so its bootstrap only ever touches the temp dir.

Session endpoints don't take an explicit `today`/`rng` (app.py always uses
"today"/an unseeded rng), so these tests drive real flows rather than pinning
exact words -- they read targets from server-side state
(store.load_current_session) since the client view never exposes `target`.
"""
from __future__ import annotations

import importlib

import pytest

from engine import store


@pytest.fixture
def client(data_root):
    import app as app_module

    importlib.reload(app_module)  # re-run module body against patched store.DATA_ROOT
    flask_app = app_module.create_app()
    flask_app.testing = True
    with flask_app.test_client() as c:
        yield c


def _current_item(student_id="default"):
    state = store.load_current_session(student_id)
    cursor = state["cursor"]
    return state["items"][cursor]["item"]


# --------------------------------------------------------------- /api/session/start
def test_session_start_returns_200_with_view(client):
    resp = client.post("/api/session/start")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["total_items"] == 10
    assert "session_id" in body
    assert "item" in body
    assert "target" not in body["item"]  # answer key never reaches the client


# --------------------------------------------------------------- /api/session/item
def test_session_item_returns_200_after_start(client):
    client.post("/api/session/start")
    resp = client.get("/api/session/item")
    assert resp.status_code == 200
    body = resp.get_json()
    assert "item" in body
    assert "target" not in body["item"]


def test_session_item_404_when_no_active_session(client):
    resp = client.get("/api/session/item")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "no_active_session"


# --------------------------------------------------------------- /api/session/answer
def test_session_answer_missing_item_id_400(client):
    client.post("/api/session/start")
    resp = client.post("/api/session/answer", json={"attempt": "cat"})
    assert resp.status_code == 400


def test_session_answer_bogus_item_id_409(client):
    client.post("/api/session/start")
    resp = client.post(
        "/api/session/answer", json={"item_id": "not-a-real-id", "attempt": "cat"}
    )
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "item_mismatch"


def test_session_answer_no_active_session_404(client):
    resp = client.post(
        "/api/session/answer", json={"item_id": "whatever", "attempt": "cat"}
    )
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "no_active_session"


def test_session_answer_correct_first_try_200(client):
    client.post("/api/session/start")
    item = _current_item()
    resp = client.post(
        "/api/session/answer", json={"item_id": item["item_id"], "attempt": item["target"]}
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["correct"] is True
    assert body["stars"] == 2
    assert body["next"] == "advance"


def test_session_answer_wrong_first_try_returns_reveal(client):
    client.post("/api/session/start")
    item = _current_item()
    resp = client.post(
        "/api/session/answer",
        json={"item_id": item["item_id"], "attempt": "definitely_wrong_xyz"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["correct"] is False
    assert body["next"] == "retry"
    assert body["reveal"]["target"] == item["target"]


def test_session_answer_past_end_of_session_409(client):
    client.post("/api/session/start")
    for _ in range(10):
        item = _current_item()
        client.post(
            "/api/session/answer", json={"item_id": item["item_id"], "attempt": item["target"]}
        )
    resp = client.post(
        "/api/session/answer", json={"item_id": "whatever", "attempt": "x"}
    )
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "session_complete"


# --------------------------------------------------------------- /api/session/finish
def test_session_finish_200_after_started_session(client):
    client.post("/api/session/start")
    resp = client.post("/api/session/finish")
    assert resp.status_code == 200
    body = resp.get_json()
    for key in ("stars", "level", "newly_introduced", "hatched", "streak"):
        assert key in body


def test_session_finish_404_when_no_session(client):
    resp = client.post("/api/session/finish")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "no_active_session"


# --------------------------------------------------------------- /api/skills
def test_skills_route_200_with_14_skills(client):
    resp = client.get("/api/skills")
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body["skills"]) == 14


# --------------------------------------------------------------- happy path flow
def test_full_happy_path_flow_through_the_api(client):
    start_resp = client.post("/api/session/start")
    assert start_resp.status_code == 200

    for _ in range(10):
        item_resp = client.get("/api/session/item")
        assert item_resp.status_code == 200
        server_item = _current_item()  # server state carries the target
        answer_resp = client.post(
            "/api/session/answer",
            json={"item_id": server_item["item_id"], "attempt": server_item["target"]},
        )
        assert answer_resp.status_code == 200
        assert answer_resp.get_json()["correct"] is True

    finish_resp = client.post("/api/session/finish")
    assert finish_resp.status_code == 200
    assert finish_resp.get_json()["correct_first_try"] == 10

    # session is now cleared
    after_resp = client.get("/api/session/item")
    assert after_resp.status_code == 404
