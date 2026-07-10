"""Tests for the answer-flow hardening (owner mandate 2026-07-09).

Covers `engine/session.py` (`submit_answer` / `_sanitize_attempt` / `_grade`),
`engine/rewards.py` (`apply_session_end` streak guard), and the
`/api/session/answer` 400 guard in `app.py`.

Every kid edge case now has a programmatic, server-derived response — the
client's claimed `phase` is NEVER trusted; the true phase is derived from
stored attempts. See engine/session.py submit_answer docstring + engine/config.py
MAX_RETYPE_TRIES/MAX_ATTEMPT_LEN/MIN_RESOLVED_FRACTION.

Follows the conventions in tests/test_session.py: explicit `today=DAY`, seeded
rng, `_server_item`/`_correct_attempt` helpers, server-state assertions via
store.load_current_session (the client view never carries `target`).
"""
from __future__ import annotations

import importlib
import random
from datetime import date

import pytest

from engine import config, contracts, rewards, session, store

DAY = date(2026, 7, 7)
SEED = 42


def _server_item(student_id, cursor=None):
    """The raw (server-side, target-included) item at the given cursor (default:
    current cursor) of the current session."""
    state = store.load_current_session(student_id)
    c = state["cursor"] if cursor is None else cursor
    return state["items"][c]["item"]


def _server_entry(student_id, cursor=None):
    state = store.load_current_session(student_id)
    c = state["cursor"] if cursor is None else cursor
    return state["items"][c]


def _correct_attempt(item):
    """A correct answer for any item type (ADR-014: bd_ninja is client-scored)."""
    if item["type"] == "bd_ninja":
        return f"{item['payload']['goal']}/0"
    return item["target"]


# =============================================================================
# 1. Refresh trick: server-derived phase, not client-claimed phase
# =============================================================================
def test_refresh_trick_correct_after_wrong_only_earns_retry_stars(bootstrapped_student):
    """A wrong first answer reveals the target. If the client then resubmits the
    CORRECT target claiming phase="first" (simulating a refresh where the
    client lies about being on a fresh attempt), the server must still treat it
    as a retry: 1 star, not 2, and correct_first_try must NOT be incremented."""
    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    item = _server_item(bootstrapped_student)

    wrong_result = session.submit_answer(
        bootstrapped_student, item["item_id"], "zzz_totally_wrong", phase="first", today=DAY
    )
    assert wrong_result["next"] == "retry"
    assert "reveal" in wrong_result

    item_after_miss = _server_item(bootstrapped_student)  # still cursor 0
    result = session.submit_answer(
        bootstrapped_student,
        item_after_miss["item_id"],
        item_after_miss["target"],
        phase="first",  # LIE: claims first-try despite the prior miss
        today=DAY,
    )
    assert result["correct"] is True
    assert result["stars"] == 1  # NOT 2 — server-derived phase wins
    assert result["next"] == "advance"
    assert result["totals"]["correct_first_try"] == 0  # not incremented


# =============================================================================
# 2. Blank guard
# =============================================================================
def test_blank_first_action_stays_no_reveal_no_attempt_recorded(bootstrapped_student):
    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    item = _server_item(bootstrapped_student)

    result = session.submit_answer(
        bootstrapped_student, item["item_id"], "   ", phase="first", today=DAY
    )
    assert result["next"] == "stay"
    assert result["nudge"] == "empty"
    assert "reveal" not in result

    entry = _server_entry(bootstrapped_student, 0)
    assert entry["attempts"] == []
    state = store.load_current_session(bootstrapped_student)
    assert state["consecutive_misses"] == 0
    assert state["cursor"] == 0  # cursor held


def test_blank_during_retry_also_stays_no_extra_attempt(bootstrapped_student):
    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    item = _server_item(bootstrapped_student)

    session.submit_answer(
        bootstrapped_student, item["item_id"], "zzz_wrong", phase="first", today=DAY
    )
    entry_after_miss = _server_entry(bootstrapped_student, 0)
    assert len(entry_after_miss["attempts"]) == 1

    result = session.submit_answer(
        bootstrapped_student, item["item_id"], "   ", phase="retry", today=DAY
    )
    assert result["next"] == "stay"
    assert result["nudge"] == "empty"
    assert "reveal" not in result

    entry_after_blank = _server_entry(bootstrapped_student, 0)
    assert len(entry_after_blank["attempts"]) == 1  # no growth
    state = store.load_current_session(bootstrapped_student)
    assert state["cursor"] == 0


# =============================================================================
# 3. Identical resubmit (double-tap)
# =============================================================================
def test_identical_resubmit_does_not_double_count(bootstrapped_student):
    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    item = _server_item(bootstrapped_student)

    session.submit_answer(
        bootstrapped_student, item["item_id"], "qqq", phase="first", today=DAY
    )
    entry_after_first_miss = _server_entry(bootstrapped_student, 0)
    attempts_count_after_miss = len(entry_after_first_miss["attempts"])
    misses_after_first = store.load_current_session(bootstrapped_student)["consecutive_misses"]

    result = session.submit_answer(
        bootstrapped_student, item["item_id"], "qqq", phase="retry", today=DAY
    )
    assert result["next"] == "stay"
    assert result["nudge"] == "same_again"

    entry_after_resubmit = _server_entry(bootstrapped_student, 0)
    assert len(entry_after_resubmit["attempts"]) == attempts_count_after_miss  # no growth
    state = store.load_current_session(bootstrapped_student)
    assert state["consecutive_misses"] == misses_after_first  # not double-counted


def test_identical_resubmit_after_normalization_case_and_punctuation(bootstrapped_student):
    """'QQQ.' normalizes to the same string as 'qqq' (case + punctuation
    forgiveness applies to the same-again check too)."""
    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    item = _server_item(bootstrapped_student)

    session.submit_answer(
        bootstrapped_student, item["item_id"], "qqq", phase="first", today=DAY
    )
    result = session.submit_answer(
        bootstrapped_student, item["item_id"], "QQQ.", phase="retry", today=DAY
    )
    assert result["next"] == "stay"
    assert result["nudge"] == "same_again"


# =============================================================================
# 4. Retype policy: MAX_RETYPE_TRIES then advance warmly
# =============================================================================
def test_retype_policy_two_distinct_wrong_copies_then_advance_with_zero_score(bootstrapped_student):
    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    item = _server_item(bootstrapped_student)
    skill_id = item["skill_id"]

    before_skills = store.load(bootstrapped_student, "skills")
    before_exposures = before_skills["skills"][skill_id]["exposures"]
    before_mastery = before_skills["skills"][skill_id]["mastery"]

    session.submit_answer(
        bootstrapped_student, item["item_id"], "zzz_wrong", phase="first", today=DAY
    )

    first_copy = session.submit_answer(
        bootstrapped_student, item["item_id"], "www", phase="retry", today=DAY
    )
    assert first_copy["next"] == "stay"
    assert first_copy["nudge"] == "copy_again"
    entry = _server_entry(bootstrapped_student, 0)
    assert entry["retype_tries"] == 1
    state = store.load_current_session(bootstrapped_student)
    assert state["cursor"] == 0  # cursor held

    second_copy = session.submit_answer(
        bootstrapped_student, item["item_id"], "eee", phase="retry", today=DAY
    )
    assert second_copy["next"] == "advance"
    assert second_copy["nudge"] == "move_on"
    assert second_copy["stars"] == 0

    state = store.load_current_session(bootstrapped_student)
    resolved_entry = state["items"][0]
    assert resolved_entry["resolved"] is True
    assert state["cursor"] == 1  # cursor advanced

    after_skills = store.load(bootstrapped_student, "skills")
    after_skill = after_skills["skills"][skill_id]
    assert after_skill["exposures"] == before_exposures + 1  # exposures grew
    # score 0 pulls the EMA toward 0 (mastery dropped or, at worst, held near baseline)
    assert after_skill["mastery"] <= before_mastery + 1e-9


# =============================================================================
# 5. Sanitization
# =============================================================================
@pytest.mark.parametrize("bad_attempt", [None, 123, {"a": 1}, ["a"], 1.5, True])
def test_sanitize_non_string_attempt_returns_bad_attempt_error(bootstrapped_student, bad_attempt):
    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    item = _server_item(bootstrapped_student)

    result = session.submit_answer(
        bootstrapped_student, item["item_id"], bad_attempt, phase="first", today=DAY
    )
    assert result == {"error": "bad_attempt"}


def test_sanitize_long_attempt_is_clamped_no_crash(bootstrapped_student):
    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    item = _server_item(bootstrapped_student)

    huge = "x" * 10_000
    result = session.submit_answer(
        bootstrapped_student, item["item_id"], huge, phase="first", today=DAY
    )
    # behaves as a normal wrong answer (huge string won't match the target)
    assert result["next"] == "retry"
    assert result["correct"] is False

    entry = _server_entry(bootstrapped_student, 0)
    stored_attempt = entry["attempts"][-1]["attempt"]
    assert len(stored_attempt) <= config.MAX_ATTEMPT_LEN


def test_sanitize_zero_width_chars_stripped_grades_correct(bootstrapped_student):
    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    item = _server_item(bootstrapped_student)
    # force a known target so we can embed a zero-width char inside it
    state = store.load_current_session(bootstrapped_student)
    state["items"][0]["item"]["target"] = "cat"
    state["items"][0]["item"]["grading"] = {
        "case_insensitive": True, "trim": True, "ignore_punctuation": True,
    }
    store.save_current_session(bootstrapped_student, state)
    item = _server_item(bootstrapped_student)

    attempt_with_zero_width = "c​at"  # zero-width space embedded
    result = session.submit_answer(
        bootstrapped_student, item["item_id"], attempt_with_zero_width, phase="first", today=DAY
    )
    assert result["correct"] is True


# =============================================================================
# 6. Punctuation forgiveness (all types)
# =============================================================================
def test_punctuation_forgiveness_target_with_trailing_period(bootstrapped_student):
    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    state = store.load_current_session(bootstrapped_student)
    state["items"][0]["item"]["target"] = "cat"
    state["items"][0]["item"]["grading"] = {
        "case_insensitive": True, "trim": True, "ignore_punctuation": True,
    }
    store.save_current_session(bootstrapped_student, state)
    item = _server_item(bootstrapped_student)

    result = session.submit_answer(
        bootstrapped_student, item["item_id"], "cat.", phase="first", today=DAY
    )
    assert result["correct"] is True
    assert result["stars"] == 2


# =============================================================================
# 7. bd_ninja forgery plausibility checks
# =============================================================================
def _bd_ninja_item(goal=5, letters_count=16):
    word_entry = {"word": "hello"}
    item = contracts.build_item("bd_ninja", "letter_orientation", word_entry, 1)
    # deterministic-ish: just trust whatever goal/letters contracts produced,
    # but read them back for correctness of assertions
    return item


def test_bd_ninja_forged_hits_greater_than_goal_incorrect():
    item = _bd_ninja_item()
    goal = item["payload"]["goal"]
    assert session._grade(item, "99/0") is False
    # sanity: goal itself is well below 99 for this fixture word
    assert goal < 99


def test_bd_ninja_exact_goal_zero_wrong_correct():
    item = _bd_ninja_item()
    goal = item["payload"]["goal"]
    assert session._grade(item, f"{goal}/0") is True


def test_bd_ninja_negative_hits_incorrect():
    item = _bd_ninja_item()
    assert session._grade(item, "-1/0") is False


def test_bd_ninja_huge_wrong_count_incorrect():
    item = _bd_ninja_item()
    goal = item["payload"]["goal"]
    assert session._grade(item, f"{goal}/999999") is False


# =============================================================================
# 8. Streak guard
# =============================================================================
def test_finish_session_streak_not_bumped_when_less_than_half_resolved(bootstrapped_student):
    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    # resolve only 1 of 10 items (< half)
    item = _server_item(bootstrapped_student)
    session.submit_answer(
        bootstrapped_student, item["item_id"], _correct_attempt(item), phase="first", today=DAY
    )
    rewards_before = store.load(bootstrapped_student, "rewards")
    streak_before = rewards_before["streak"]["count"]

    session.finish_session(bootstrapped_student, today=DAY)

    rewards_after = store.load(bootstrapped_student, "rewards")
    assert rewards_after["streak"]["count"] == streak_before  # unchanged


def test_finish_session_streak_bumped_when_at_least_half_resolved_next_day(bootstrapped_student):
    day1 = DAY
    day2 = date(2026, 7, 8)

    # day 1: resolve at least half (establishes last_day)
    session.start_session(bootstrapped_student, today=day1, rng=random.Random(SEED))
    for _ in range(5):
        item = _server_item(bootstrapped_student)
        session.submit_answer(
            bootstrapped_student, item["item_id"], _correct_attempt(item), phase="first", today=day1
        )
    session.finish_session(bootstrapped_student, today=day1)
    streak_after_day1 = store.load(bootstrapped_student, "rewards")["streak"]["count"]

    # day 2: resolve at least half again -> streak should increase (consecutive day)
    session.start_session(bootstrapped_student, today=day2, rng=random.Random(SEED))
    for _ in range(5):
        item = _server_item(bootstrapped_student)
        session.submit_answer(
            bootstrapped_student, item["item_id"], _correct_attempt(item), phase="first", today=day2
        )
    session.finish_session(bootstrapped_student, today=day2)
    streak_after_day2 = store.load(bootstrapped_student, "rewards")["streak"]["count"]

    assert streak_after_day2 == streak_after_day1 + 1


def test_apply_session_end_count_streak_false_leaves_streak_untouched_but_still_hatches(bootstrapped_student):
    rewards_doc = store.load(bootstrapped_student, "rewards")
    streak_before = dict(rewards_doc["streak"])

    skills_doc = store.load(bootstrapped_student, "skills")
    skills_doc["skills"]["short_vowels"]["mastery"] = 90
    skills_doc["skills"]["short_vowels"]["last_practiced"] = DAY.isoformat()

    previous_masteries = {"short_vowels": 90}

    result = rewards.apply_session_end(
        rewards_doc, skills_doc, previous_masteries, DAY, count_streak=False
    )

    assert result["streak"] == streak_before  # streak untouched
    hatched_ids = {c["skill_id"] for c in result["collection"]}
    assert "short_vowels" in hatched_ids  # hatching still runs


# =============================================================================
# 9. API: non-string attempt -> 400 before reaching the engine
# =============================================================================
@pytest.fixture
def client(data_root):
    import app as app_module

    importlib.reload(app_module)  # re-run module body against patched store.DATA_ROOT
    flask_app = app_module.create_app()
    flask_app.testing = True
    with flask_app.test_client() as c:
        yield c


def test_api_session_answer_non_string_attempt_400(client):
    client.post("/api/session/start")
    state = store.load_current_session("default")
    item_id = state["items"][0]["item"]["item_id"]

    resp = client.post(
        "/api/session/answer", json={"item_id": item_id, "attempt": {"x": 1}}
    )
    assert resp.status_code == 400


# =============================================================================
# 10. Response messages: non-empty kid-voice "message" on stay/move_on
# =============================================================================
def test_empty_nudge_has_nonempty_message(bootstrapped_student):
    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    item = _server_item(bootstrapped_student)
    result = session.submit_answer(
        bootstrapped_student, item["item_id"], "   ", phase="first", today=DAY
    )
    assert result.get("message")
    assert isinstance(result["message"], str) and result["message"].strip() != ""


def test_same_again_nudge_has_nonempty_message(bootstrapped_student):
    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    item = _server_item(bootstrapped_student)
    session.submit_answer(
        bootstrapped_student, item["item_id"], "qqq", phase="first", today=DAY
    )
    result = session.submit_answer(
        bootstrapped_student, item["item_id"], "qqq", phase="retry", today=DAY
    )
    assert result.get("message")
    assert isinstance(result["message"], str) and result["message"].strip() != ""


def test_copy_again_nudge_has_nonempty_message(bootstrapped_student):
    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    item = _server_item(bootstrapped_student)
    session.submit_answer(
        bootstrapped_student, item["item_id"], "zzz_wrong", phase="first", today=DAY
    )
    result = session.submit_answer(
        bootstrapped_student, item["item_id"], "www", phase="retry", today=DAY
    )
    assert result.get("message")
    assert isinstance(result["message"], str) and result["message"].strip() != ""


def test_move_on_nudge_has_nonempty_message(bootstrapped_student):
    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    item = _server_item(bootstrapped_student)
    session.submit_answer(
        bootstrapped_student, item["item_id"], "zzz_wrong", phase="first", today=DAY
    )
    session.submit_answer(
        bootstrapped_student, item["item_id"], "www", phase="retry", today=DAY
    )
    result = session.submit_answer(
        bootstrapped_student, item["item_id"], "eee", phase="retry", today=DAY
    )
    assert result.get("message")
    assert isinstance(result["message"], str) and result["message"].strip() != ""
