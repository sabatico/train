"""Tests for engine/session.py — the ADR-009 session lifecycle.

start_session/get_item/submit_answer/finish_session, step-down, mastery
persistence, and hatching. Grading is server-side (client view hides `target`),
so tests read server state (`store.load_current_session`) to get targets. All
time-dependent calls pass an explicit `today` for determinism; `start_session`
also takes a seeded `rng`.
"""
from __future__ import annotations

import random
from datetime import date

from engine import config, session, store

DAY = date(2026, 7, 7)
SEED = 42


def _server_item(student_id, cursor=None):
    """The raw (server-side, target-included) item at the given cursor (default:
    current cursor) of the current session."""
    state = store.load_current_session(student_id)
    c = state["cursor"] if cursor is None else cursor
    return state["items"][c]["item"]


def _correct_attempt(item):
    """A correct answer for any item type (ADR-014: bd_ninja is client-scored)."""
    if item["type"] == "bd_ninja":
        return f"{item['payload']['goal']}/0"
    return item["target"]


# --------------------------------------------------------------- start_session
def test_start_session_builds_full_item_count(bootstrapped_student):
    view = session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    assert view["total_items"] == config.ITEMS_PER_SESSION == 10


def test_start_session_focus_skill_has_word_bank_content(bootstrapped_student):
    view = session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    focus = view["focus_skill"]
    assert focus is not None
    skills_doc = store.load(bootstrapped_student, "skills")
    assert skills_doc["skills"][focus]["introduced"] is True
    # regression guard: focus must have actual content, never an empty skill
    # (ADR-014: bankless skills draw from the content provider, not their own bank)
    from engine import selector as sel
    content = sel.make_content_provider(skills_doc, store.load_word_bank, DAY)
    assert content(focus) != []


def test_start_session_teach_examples_are_words_from_focus_skill(bootstrapped_student):
    view = session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    focus = view["focus_skill"]
    from engine import selector as sel
    skills_doc = store.load(bootstrapped_student, "skills")
    content = sel.make_content_provider(skills_doc, store.load_word_bank, DAY)
    provider_words = {w["word"] for w in content(focus)}
    assert view["teach"]["skill_id"] == focus
    assert len(view["teach"]["examples"]) > 0
    for ex in view["teach"]["examples"]:
        assert ex in provider_words


def test_start_session_writes_current_session_file(bootstrapped_student):
    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    sdir = store.student_dir(bootstrapped_student)
    assert (sdir / "sessions" / "current.json").exists()


def test_start_session_same_day_resumes_same_session_id(bootstrapped_student):
    v1 = session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    v2 = session.start_session(bootstrapped_student, today=DAY, rng=random.Random(999))
    assert v1["session_id"] == v2["session_id"]


def test_start_session_resume_preserves_cursor_progress(bootstrapped_student):
    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    item = _server_item(bootstrapped_student)
    session.submit_answer(
        bootstrapped_student, item["item_id"], item["target"], phase="first", today=DAY
    )
    resumed = session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    assert resumed["cursor"] == 1


def test_start_session_stale_session_replaced_with_new_id(bootstrapped_student):
    v1 = session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    next_day = date(2026, 7, 8)
    v2 = session.start_session(bootstrapped_student, today=next_day, rng=random.Random(SEED))
    assert v1["session_id"] != v2["session_id"]
    assert v2["cursor"] == 0


# --------------------------------------------------------------- get_item
def test_get_item_view_has_no_target(bootstrapped_student):
    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    view = session.get_item(bootstrapped_student)
    assert "target" not in view["item"]


def test_get_item_returns_none_when_no_current_session(bootstrapped_student):
    assert session.get_item(bootstrapped_student) is None


# --------------------------------------------------------------- submit_answer: correct first try
def test_submit_answer_correct_first_try(bootstrapped_student):
    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    before_skills = store.load(bootstrapped_student, "skills")
    item = _server_item(bootstrapped_student)
    skill_id = item["skill_id"]
    before_mastery = before_skills["skills"][skill_id]["mastery"]
    before_exposures = before_skills["skills"][skill_id]["exposures"]

    result = session.submit_answer(
        bootstrapped_student, item["item_id"], item["target"], phase="first", today=DAY
    )
    assert result["correct"] is True
    assert result["stars"] == 2
    assert result["next"] == "advance"
    assert result["totals"]["correct_first_try"] == 1

    state = store.load_current_session(bootstrapped_student)
    assert state["cursor"] == 1

    after_skills = store.load(bootstrapped_student, "skills")
    assert after_skills["skills"][skill_id]["mastery"] > before_mastery
    assert after_skills["skills"][skill_id]["exposures"] == before_exposures + 1


def test_submit_answer_survives_missing_skill_record(bootstrapped_student):
    """Defensive branch: if the item's skill_id is somehow absent from
    skills.json (shouldn't normally happen -- plans are built from introduced
    skills), grading must still complete without crashing, just skip the
    mastery update."""
    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    item = _server_item(bootstrapped_student)
    skill_id = item["skill_id"]

    skills_doc = store.load(bootstrapped_student, "skills")
    del skills_doc["skills"][skill_id]
    store.save(bootstrapped_student, "skills", skills_doc)

    result = session.submit_answer(
        bootstrapped_student, item["item_id"], item["target"], phase="first", today=DAY
    )
    assert result["correct"] is True
    assert result["stars"] == 2
    # the skill record must still be absent, not resurrected
    after_skills = store.load(bootstrapped_student, "skills")
    assert skill_id not in after_skills["skills"]


# --------------------------------------------------------------- submit_answer: wrong first try
def test_submit_answer_wrong_first_try(bootstrapped_student):
    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    item = _server_item(bootstrapped_student)

    result = session.submit_answer(
        bootstrapped_student, item["item_id"], "zzz_totally_wrong", phase="first", today=DAY
    )
    assert result["next"] == "retry"
    assert result["stars"] == 0
    assert result["correct"] is False

    state = store.load_current_session(bootstrapped_student)
    assert state["cursor"] == 0  # cursor did not advance

    reveal = result["reveal"]
    assert reveal["target"] == item["target"]
    assert "markers" in reveal
    assert "why" in reveal
    assert "audio" in reveal


# --------------------------------------------------------------- retype (phase="retry")
def test_retype_correct_gives_one_star_and_advances(bootstrapped_student):
    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    item = _server_item(bootstrapped_student)
    skill_id = item["skill_id"]

    session.submit_answer(
        bootstrapped_student, item["item_id"], "zzz_wrong", phase="first", today=DAY
    )
    item_after_miss = _server_item(bootstrapped_student)  # still cursor 0
    before_skills = store.load(bootstrapped_student, "skills")
    before_mastery = before_skills["skills"][skill_id]["mastery"]

    result = session.submit_answer(
        bootstrapped_student,
        item_after_miss["item_id"],
        item_after_miss["target"],
        phase="retry",
        today=DAY,
    )
    assert result["correct"] is True
    assert result["stars"] == 1
    assert result["next"] == "advance"

    state = store.load_current_session(bootstrapped_student)
    assert state["cursor"] == 1

    after_skills = store.load(bootstrapped_student, "skills")
    # corrected score (0.5) still moves mastery up from wherever it was
    assert after_skills["skills"][skill_id]["mastery"] != before_mastery


def test_retype_wrong_still_advances_never_traps(bootstrapped_student):
    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    item = _server_item(bootstrapped_student)

    session.submit_answer(
        bootstrapped_student, item["item_id"], "zzz_wrong", phase="first", today=DAY
    )
    item_after_miss = _server_item(bootstrapped_student)
    result = session.submit_answer(
        bootstrapped_student, item_after_miss["item_id"], "still_wrong", phase="retry", today=DAY
    )
    assert result["stars"] == 0
    assert result["next"] == "advance"

    state = store.load_current_session(bootstrapped_student)
    assert state["cursor"] == 1  # advanced despite the wrong retype


# --------------------------------------------------------------- errors
def test_submit_answer_item_mismatch(bootstrapped_student):
    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    result = session.submit_answer(
        bootstrapped_student, "not-a-real-item-id", "whatever", phase="first", today=DAY
    )
    assert result["error"] == "item_mismatch"


def test_submit_answer_no_active_session(bootstrapped_student):
    result = session.submit_answer(
        bootstrapped_student, "some-item-id", "whatever", phase="first", today=DAY
    )
    assert result == {"error": "no_active_session"}


def test_submit_answer_past_end_of_session(bootstrapped_student):
    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    # answer every item correctly (reading targets from server state each time)
    for _ in range(config.ITEMS_PER_SESSION):
        item = _server_item(bootstrapped_student)
        session.submit_answer(
            bootstrapped_student, item["item_id"], _correct_attempt(item), phase="first", today=DAY
        )
    state = store.load_current_session(bootstrapped_student)
    assert state["cursor"] == config.ITEMS_PER_SESSION

    result = session.submit_answer(
        bootstrapped_student, "irrelevant-id", "whatever", phase="first", today=DAY
    )
    assert result == {"error": "session_complete"}


# --------------------------------------------------------------- step-down
def test_step_down_after_two_consecutive_first_try_misses(bootstrapped_student):
    """Boost mastery so the plan starts with a less-scaffolded exercise type,
    then drive two consecutive first-try misses and confirm the NEXT unanswered
    item is rebuilt as the most-scaffolded type at scaffold_level 1."""
    skills_doc = store.load(bootstrapped_student, "skills")
    skills_doc["skills"]["short_vowels"]["mastery"] = 90
    skills_doc["skills"]["heart_words"]["mastery"] = 90
    store.save(bootstrapped_student, "skills", skills_doc)

    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    state = store.load_current_session(bootstrapped_student)
    # sanity: at least one of the first two items must NOT already be the most
    # scaffolded type, else the assertion below wouldn't prove anything
    assert any(
        state["items"][i]["item"]["type"] != config.SCAFFOLD_TYPES[0] for i in (0, 1)
    )

    # miss #1 (first try) + a correct retype (doesn't reset consecutive_misses)
    item0 = _server_item(bootstrapped_student, 0)
    session.submit_answer(
        bootstrapped_student, item0["item_id"], "zzz_wrong", phase="first", today=DAY
    )
    item0_retry = _server_item(bootstrapped_student, 0)
    session.submit_answer(
        bootstrapped_student, item0_retry["item_id"], item0_retry["target"], phase="retry", today=DAY
    )

    # miss #2 (first try) on the now-current item (cursor 1)
    item1 = _server_item(bootstrapped_student, 1)
    session.submit_answer(
        bootstrapped_student, item1["item_id"], "zzz_wrong_again", phase="first", today=DAY
    )

    state = store.load_current_session(bootstrapped_student)
    next_item = state["items"][2]["item"]
    assert next_item["type"] == config.SCAFFOLD_TYPES[0] == "word_builder"
    assert next_item["scaffold_level"] == 1


# --------------------------------------------------------------- finish_session
def test_finish_session_writes_log_with_end_masteries(bootstrapped_student):
    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    session.finish_session(bootstrapped_student, today=DAY)

    logs = store.list_session_logs(bootstrapped_student)
    assert DAY.isoformat() in logs
    log = store.load_session_log(bootstrapped_student, DAY.isoformat())
    assert "end_masteries" in log
    assert isinstance(log["end_masteries"], dict)


def test_finish_session_clears_current_session(bootstrapped_student):
    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    session.finish_session(bootstrapped_student, today=DAY)
    assert session.get_item(bootstrapped_student) is None


def test_finish_session_returns_summary_fields(bootstrapped_student):
    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    result = session.finish_session(bootstrapped_student, today=DAY)
    for key in ("stars", "level", "newly_introduced", "hatched", "streak"):
        assert key in result


def test_finish_session_no_active_session(bootstrapped_student):
    result = session.finish_session(bootstrapped_student, today=DAY)
    assert result == {"error": "no_active_session"}


# --------------------------------------------------------------- hatching integration
def test_finish_session_hatches_sustained_mastery_skill(bootstrapped_student):
    # prior session's end_masteries already had short_vowels >= 85
    store.write_session_log(
        bootstrapped_student, {"end_masteries": {"short_vowels": 90}}, on=date(2026, 7, 6)
    )
    # current stored mastery also >= 85, practiced today (no decay)
    skills_doc = store.load(bootstrapped_student, "skills")
    skills_doc["skills"]["short_vowels"]["mastery"] = 90
    skills_doc["skills"]["short_vowels"]["last_practiced"] = DAY.isoformat()
    store.save(bootstrapped_student, "skills", skills_doc)

    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    result = session.finish_session(bootstrapped_student, today=DAY)

    assert "short_vowels" in result["hatched"]
    rewards_doc = store.load(bootstrapped_student, "rewards")
    hatched_skill_ids = {c["skill_id"] for c in rewards_doc["collection"]}
    assert "short_vowels" in hatched_skill_ids


def test_finish_session_does_not_hatch_without_sustained_mastery(bootstrapped_student):
    # current mastery high, but NO prior session log at all -> not sustained
    skills_doc = store.load(bootstrapped_student, "skills")
    skills_doc["skills"]["short_vowels"]["mastery"] = 90
    skills_doc["skills"]["short_vowels"]["last_practiced"] = DAY.isoformat()
    store.save(bootstrapped_student, "skills", skills_doc)

    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    result = session.finish_session(bootstrapped_student, today=DAY)

    assert "short_vowels" not in result["hatched"]


# --------------------------------------------------------------- store.load_session_log
def test_load_session_log_returns_written_log(bootstrapped_student):
    store.write_session_log(bootstrapped_student, {"stars": 9}, on=date(2026, 7, 3))
    log = store.load_session_log(bootstrapped_student, "2026-07-03")
    assert log == {"stars": 9}


def test_load_session_log_missing_date_returns_none(bootstrapped_student):
    assert store.load_session_log(bootstrapped_student, "2099-01-01") is None
