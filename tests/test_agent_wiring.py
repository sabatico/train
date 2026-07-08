"""Tests for the agent's wiring INTO the deterministic session engine
(engine/session.py, ADR-012):

- a first-try miss's `reveal["why"]` falls back to the item's canned
  `text_fallback` when the agent is off (default/deterministic path, must
  keep working exactly as before B8),
- the same path calls through to `agent.teacher.feedback_for` and uses its
  return value when the agent is (mock-)available,
- `finish_session` appends a dated note to the teacher notebook
  (`store.append_memory` / `store.read_memory`).

No real network call is made anywhere in this file — `agent.teacher.feedback_for`
is monkeypatched directly rather than the underlying client.
"""
from __future__ import annotations

import random
from datetime import date

from agent import teacher
from engine import session, store

DAY = date(2026, 7, 7)
SEED = 42


def _server_item(student_id, cursor=None):
    state = store.load_current_session(student_id)
    c = state["cursor"] if cursor is None else cursor
    return state["items"][c]["item"]


# --------------------------------------------------------------- fallback (agent off)
def test_first_try_miss_reveal_why_is_canned_fallback_when_agent_off(
    bootstrapped_student, monkeypatch
):
    monkeypatch.delenv("SPELLQUEST_AGENT_LIVE", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    item = _server_item(bootstrapped_student)

    result = session.submit_answer(
        bootstrapped_student, item["item_id"], "zzz_totally_wrong", phase="first", today=DAY
    )

    assert result["next"] == "retry"
    assert result["reveal"]["why"] == item["why"]["text_fallback"]


def test_first_try_miss_never_calls_agent_when_off(bootstrapped_student, monkeypatch):
    """Belt-and-braces: with the agent unavailable, feedback_for degrades to
    the canned line without needing a network mock at all -- confirming the
    wiring doesn't bypass teacher.is_available()."""
    monkeypatch.delenv("SPELLQUEST_AGENT_LIVE", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    def _boom(*args, **kwargs):
        raise AssertionError("agent.client.chat should not be reached when agent is off")

    from agent import client

    monkeypatch.setattr(client, "chat", _boom)

    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    item = _server_item(bootstrapped_student)
    result = session.submit_answer(
        bootstrapped_student, item["item_id"], "zzz_totally_wrong", phase="first", today=DAY
    )
    assert result["reveal"]["why"] == item["why"]["text_fallback"]


# --------------------------------------------------------------- wiring proof (mocked teacher)
def test_first_try_miss_reveal_why_uses_teacher_feedback_when_available(
    bootstrapped_student, monkeypatch
):
    sentinel = "Sentinel: silent e makes the vowel say its name!"

    def _fake_feedback_for(target, primary_tag, rule_id, canned, *, timeout=4.0):
        return sentinel

    monkeypatch.setattr(teacher, "feedback_for", _fake_feedback_for)
    # session.py does `from agent import teacher` then calls `teacher.feedback_for`,
    # so patching the attribute on the shared `agent.teacher` module object (as
    # above) is visible through `engine.session.teacher` too since it's the same
    # module object. Patch both by name to be robust against either import style.
    monkeypatch.setattr(session.teacher, "feedback_for", _fake_feedback_for)

    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    item = _server_item(bootstrapped_student)

    result = session.submit_answer(
        bootstrapped_student, item["item_id"], "zzz_totally_wrong", phase="first", today=DAY
    )

    assert result["next"] == "retry"
    assert result["reveal"]["why"] == sentinel


def test_first_try_miss_calls_teacher_with_target_tag_and_rule(bootstrapped_student, monkeypatch):
    captured = {}

    def _fake_feedback_for(target, primary_tag, rule_id, canned, *, timeout=4.0):
        captured["target"] = target
        captured["primary_tag"] = primary_tag
        captured["rule_id"] = rule_id
        captured["canned"] = canned
        return canned

    monkeypatch.setattr(session.teacher, "feedback_for", _fake_feedback_for)

    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    item = _server_item(bootstrapped_student)

    session.submit_answer(
        bootstrapped_student, item["item_id"], "zzz_totally_wrong", phase="first", today=DAY
    )

    assert captured["target"] == item["target"]
    assert captured["rule_id"] == item["why"]["rule_id"]
    assert captured["canned"] == item["why"]["text_fallback"]


# --------------------------------------------------------------- finish_session -> memory notebook
def test_finish_session_appends_note_to_teacher_notebook(bootstrapped_student):
    assert store.read_memory(bootstrapped_student) == ""

    view = session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    focus_skill = view["focus_skill"]

    # drive every item to completion (correct first try) so finish_session has
    # a real, deterministic session to close out.
    for _ in range(len(store.load_current_session(bootstrapped_student)["items"])):
        item = _server_item(bootstrapped_student)
        session.submit_answer(
            bootstrapped_student, item["item_id"], item["target"], phase="first", today=DAY
        )

    session.finish_session(bootstrapped_student, today=DAY)

    memory = store.read_memory(bootstrapped_student)
    assert memory != ""
    assert focus_skill in memory
    assert DAY.isoformat() in memory
