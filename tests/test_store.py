"""Tests for engine/store.py — the ONLY module allowed to touch data/.

Protects invariant #1: NO CHILD DATA LOSS. Highest-value test target in this
suite — covers bootstrap idempotence, atomic writes, path-traversal safety,
round-trip persistence, and the missing-file-returns-defaults contract.
"""
from __future__ import annotations

import json

import pytest

from engine import config, models, store

NO_PREREQ_SKILLS = {"letter_orientation", "phoneme_segmentation", "short_vowels", "heart_words"}


# ------------------------------------------------------------- bootstrap_student
def test_bootstrap_creates_14_skills(bootstrapped_student):
    skills = store.load(bootstrapped_student, "skills")["skills"]
    assert len(skills) == 14
    assert set(skills.keys()) == set(config.SKILL_IDS)


def test_bootstrap_introduces_exactly_the_four_no_prereq_skills(bootstrapped_student):
    skills = store.load(bootstrapped_student, "skills")["skills"]
    introduced = {sid for sid, rec in skills.items() if rec["introduced"]}
    assert introduced == NO_PREREQ_SKILLS
    for sid in NO_PREREQ_SKILLS:
        assert skills[sid]["mastery"] == 20
    for sid in set(config.SKILL_IDS) - NO_PREREQ_SKILLS:
        assert skills[sid]["introduced"] is False
        assert skills[sid]["mastery"] == 0


def test_bootstrap_magic_e_not_introduced(bootstrapped_student):
    # named explicitly per the task brief's cautionary example
    skills = store.load(bootstrapped_student, "skills")["skills"]
    assert skills["magic_e"]["introduced"] is False


def test_bootstrap_creates_sessions_and_logs_dirs(data_root):
    store.bootstrap_student("kiddo")
    sdir = store.student_dir("kiddo")
    assert (sdir / "sessions").is_dir()
    assert (sdir / "logs").is_dir()
    assert (sdir / "profile.json").exists()
    assert (sdir / "skills.json").exists()
    assert (sdir / "rewards.json").exists()


def test_bootstrap_is_idempotent_never_overwrites(bootstrapped_student):
    # simulate real progress: mutate a skill and save it
    skills_doc = store.load(bootstrapped_student, "skills")
    skills_doc["skills"]["short_vowels"]["mastery"] = 77
    skills_doc["skills"]["short_vowels"]["exposures"] = 12
    store.save(bootstrapped_student, "skills", skills_doc)

    # also mutate rewards and profile to be thorough
    rewards_doc = store.load(bootstrapped_student, "rewards")
    rewards_doc["stars_total"] = 42
    store.save(bootstrapped_student, "rewards", rewards_doc)

    profile_doc = store.load(bootstrapped_student, "profile")
    profile_doc["display_name"] = "Iris"
    store.save(bootstrapped_student, "profile", profile_doc)

    # re-bootstrap must NOT clobber any of this — invariant #1
    store.bootstrap_student(bootstrapped_student)

    reloaded_skills = store.load(bootstrapped_student, "skills")
    assert reloaded_skills["skills"]["short_vowels"]["mastery"] == 77
    assert reloaded_skills["skills"]["short_vowels"]["exposures"] == 12

    reloaded_rewards = store.load(bootstrapped_student, "rewards")
    assert reloaded_rewards["stars_total"] == 42

    reloaded_profile = store.load(bootstrapped_student, "profile")
    assert reloaded_profile["display_name"] == "Iris"


def test_bootstrap_called_twice_in_a_row_is_a_noop(data_root):
    store.bootstrap_student("kiddo")
    store.bootstrap_student("kiddo")  # must not raise, must not change anything
    skills = store.load("kiddo", "skills")["skills"]
    assert skills["short_vowels"]["mastery"] == 20


# ------------------------------------------------------------- save/load round-trip
@pytest.mark.parametrize("doc", ["profile", "skills", "rewards"])
def test_save_load_round_trip(data_root, doc):
    store.bootstrap_student("kiddo")
    original = store.load("kiddo", doc)
    original_copy = json.loads(json.dumps(original))  # deep copy via JSON
    store.save("kiddo", doc, original)
    reloaded = store.load("kiddo", doc)
    assert reloaded == original_copy


def test_save_then_load_reflects_mutation(bootstrapped_student):
    rewards = store.load(bootstrapped_student, "rewards")
    rewards["xp"] = 123
    rewards["level"] = 3
    store.save(bootstrapped_student, "rewards", rewards)
    reloaded = store.load(bootstrapped_student, "rewards")
    assert reloaded["xp"] == 123
    assert reloaded["level"] == 3


def test_load_missing_doc_returns_fresh_defaults(data_root):
    # a student dir that was NEVER bootstrapped
    profile = store.load("never_seen", "profile")
    assert profile == models.default_profile()

    rewards = store.load("never_seen", "rewards")
    assert rewards == models.default_rewards()

    skills = store.load("never_seen", "skills")
    # load_skill_graph() succeeds here because data_root has a seeded word_bank/
    assert skills == models.default_skills(store.load_skill_graph())
    assert skills["skills"]["short_vowels"]["introduced"] is True
    assert skills["skills"]["magic_e"]["introduced"] is False


def test_load_missing_doc_does_not_create_a_file(data_root):
    store.load("ghost", "profile")
    assert not (store.student_dir("ghost") / "profile.json").exists()


def test_load_unknown_doc_raises_key_error(bootstrapped_student):
    with pytest.raises(KeyError):
        store.load(bootstrapped_student, "not_a_real_doc")


def test_save_unknown_doc_raises_key_error(bootstrapped_student):
    with pytest.raises(KeyError):
        store.save(bootstrapped_student, "not_a_real_doc", {})


# ------------------------------------------------------------- atomic write
def test_save_produces_valid_json_and_no_leftover_tmp_files(bootstrapped_student):
    rewards = store.load(bootstrapped_student, "rewards")
    rewards["xp"] = 55
    store.save(bootstrapped_student, "rewards", rewards)

    sdir = store.student_dir(bootstrapped_student)
    rewards_path = sdir / "rewards.json"
    assert rewards_path.exists()
    with rewards_path.open() as f:
        parsed = json.load(f)  # must not raise -- valid JSON
    assert parsed["xp"] == 55

    leftover_tmp = list(sdir.glob(".tmp-*"))
    assert leftover_tmp == [], f"atomic write left temp file(s) behind: {leftover_tmp}"


def test_multiple_saves_leave_no_tmp_residue(bootstrapped_student):
    for i in range(5):
        rewards = store.load(bootstrapped_student, "rewards")
        rewards["xp"] = i
        store.save(bootstrapped_student, "rewards", rewards)
    sdir = store.student_dir(bootstrapped_student)
    assert list(sdir.glob(".tmp-*")) == []
    assert list(sdir.glob("*.tmp")) == []


def test_atomic_write_swallows_secondary_unlink_failure(bootstrapped_student, monkeypatch):
    """Belt-and-suspenders branch: if os.replace() fails AND the best-effort
    os.unlink(tmp) cleanup *also* fails, _atomic_write must still raise the
    ORIGINAL error (not the secondary OSError) rather than crashing weirdly."""
    import os as os_module

    def boom_replace(*args, **kwargs):
        raise OSError("simulated replace failure")

    def boom_unlink(*args, **kwargs):
        raise OSError("simulated unlink failure (tmp already gone)")

    monkeypatch.setattr(store.os, "replace", boom_replace)
    monkeypatch.setattr(store.os, "unlink", boom_unlink)
    with pytest.raises(OSError, match="simulated replace failure"):
        store.save(bootstrapped_student, "rewards", {"xp": 1})


def test_atomic_write_cleans_up_tmp_file_on_failure(bootstrapped_student, monkeypatch):
    """If os.replace() blows up mid-write, no .tmp-* file should survive."""
    import os as os_module

    sdir = store.student_dir(bootstrapped_student)
    real_replace = os_module.replace

    def boom(*args, **kwargs):
        raise OSError("simulated failure")

    monkeypatch.setattr(store.os, "replace", boom)
    with pytest.raises(OSError):
        store.save(bootstrapped_student, "rewards", {"xp": 1})
    monkeypatch.setattr(store.os, "replace", real_replace)

    assert list(sdir.glob(".tmp-*")) == []
    # and the original file (from bootstrap) must be untouched/intact
    original = store.load(bootstrapped_student, "rewards")
    assert original == models.default_rewards()


# ------------------------------------------------------------- path safety
@pytest.mark.parametrize(
    "bad_id",
    ["../evil", "/etc", "a/b", "", "..", "CAPITAL", "has space", "semi;colon"],
)
def test_student_dir_rejects_unsafe_ids(data_root, bad_id):
    with pytest.raises(ValueError):
        store.student_dir(bad_id)


def test_student_dir_rejects_non_str_input(data_root):
    for bad in (None, 123, ["default"], {"id": "default"}):
        with pytest.raises(ValueError):
            store.student_dir(bad)


@pytest.mark.parametrize(
    "bad_id",
    ["../evil", "/etc", "a/b", ""],
)
def test_public_functions_reject_unsafe_student_id(data_root, bad_id):
    with pytest.raises(ValueError):
        store.load(bad_id, "profile")
    with pytest.raises(ValueError):
        store.save(bad_id, "profile", {})
    with pytest.raises(ValueError):
        store.append_memory(bad_id, "note")
    with pytest.raises(ValueError):
        store.read_memory(bad_id)
    with pytest.raises(ValueError):
        store.bootstrap_student(bad_id)
    with pytest.raises(ValueError):
        store.load_current_session(bad_id)
    with pytest.raises(ValueError):
        store.save_current_session(bad_id, {})
    with pytest.raises(ValueError):
        store.clear_current_session(bad_id)
    with pytest.raises(ValueError):
        store.write_session_log(bad_id, {})
    with pytest.raises(ValueError):
        store.list_session_logs(bad_id)


def test_student_dir_accepts_valid_slug(data_root):
    p = store.student_dir("default")
    assert p == data_root / "students" / "default"


def test_load_word_bank_rejects_traversal_pattern(data_root):
    with pytest.raises(ValueError):
        store.load_word_bank("../evil")


# ------------------------------------------------------------- memory notebook
def test_read_memory_on_fresh_student_returns_empty_string(data_root):
    assert store.read_memory("fresh_kid") == ""


def test_append_memory_is_dated_and_cumulative(bootstrapped_student):
    from datetime import date

    store.append_memory(bootstrapped_student, "loves emoji rewards", on=date(2026, 7, 1))
    store.append_memory(bootstrapped_student, "struggles with magic e", on=date(2026, 7, 3))

    text = store.read_memory(bootstrapped_student)
    assert "2026-07-01" in text
    assert "loves emoji rewards" in text
    assert "2026-07-03" in text
    assert "struggles with magic e" in text
    # both entries present simultaneously (cumulative, not overwritten)
    assert text.index("2026-07-01") < text.index("2026-07-03")


def test_append_memory_defaults_to_today(bootstrapped_student):
    import datetime

    store.append_memory(bootstrapped_student, "note without explicit date")
    text = store.read_memory(bootstrapped_student)
    today = datetime.date.today().isoformat()
    assert today in text


# ------------------------------------------------------------- session helpers
def test_current_session_round_trip(bootstrapped_student):
    assert store.load_current_session(bootstrapped_student) is None
    session = {"focus_skill": "short_vowels", "items": []}
    store.save_current_session(bootstrapped_student, session)
    assert store.load_current_session(bootstrapped_student) == session


def test_clear_current_session_makes_it_none(bootstrapped_student):
    store.save_current_session(bootstrapped_student, {"foo": "bar"})
    store.clear_current_session(bootstrapped_student)
    assert store.load_current_session(bootstrapped_student) is None


def test_clear_current_session_safe_when_absent(bootstrapped_student):
    # never saved -- must not raise
    store.clear_current_session(bootstrapped_student)
    assert store.load_current_session(bootstrapped_student) is None


def test_write_session_log_and_list_session_logs(bootstrapped_student):
    from datetime import date

    store.write_session_log(bootstrapped_student, {"stars": 5}, on=date(2026, 7, 2))
    store.write_session_log(bootstrapped_student, {"stars": 3}, on=date(2026, 7, 1))
    store.write_session_log(bootstrapped_student, {"stars": 7}, on=date(2026, 7, 5))

    logs = store.list_session_logs(bootstrapped_student)
    assert logs == ["2026-07-01", "2026-07-02", "2026-07-05"]  # sorted


def test_write_session_log_returns_date_key(bootstrapped_student):
    from datetime import date

    key = store.write_session_log(bootstrapped_student, {"stars": 1}, on=date(2026, 7, 4))
    assert key == "2026-07-04"


def test_list_session_logs_excludes_current(bootstrapped_student):
    store.save_current_session(bootstrapped_student, {"in_flight": True})
    from datetime import date

    store.write_session_log(bootstrapped_student, {"stars": 2}, on=date(2026, 7, 6))

    logs = store.list_session_logs(bootstrapped_student)
    assert "current" not in logs
    assert logs == ["2026-07-06"]


def test_list_session_logs_empty_for_fresh_student(data_root):
    assert store.list_session_logs("brand_new") == []


# ------------------------------------------------------------- word bank / skill graph
def test_load_word_bank_seeded_pattern_returns_words(data_root):
    words = store.load_word_bank("short_vowels")
    assert len(words) >= 1
    assert words[0]["word"] == "cat"


def test_load_word_bank_missing_pattern_returns_empty_list(data_root):
    assert store.load_word_bank("nonexistent_pattern") == []


def test_load_skill_graph_returns_14_keys(data_root):
    graph = store.load_skill_graph()
    assert len(graph) == 14
    assert set(graph.keys()) == set(config.SKILL_IDS)


def test_load_skill_graph_missing_returns_empty_dict(empty_data_root):
    assert store.load_skill_graph() == {}


def test_load_word_bank_missing_word_bank_dir_returns_empty_list(empty_data_root):
    assert store.load_word_bank("short_vowels") == []


# ------------------------------------------------------------- guardrail: no bypass writes
def test_guardrail_no_direct_data_writes_outside_store():
    """Invariant #1 guardrail: no engine module (other than store.py) or app.py
    should write files directly -- every persisted byte must go through store.py's
    atomic-write path. Greppable and simple by design."""
    import pathlib
    import re

    repo_root = pathlib.Path(__file__).resolve().parent.parent
    write_patterns = [
        re.compile(r"""open\([^)]*['"]w"""),  # open(..., "w"...) or 'w'
        re.compile(r"\.write_text\("),
        re.compile(r"json\.dump\("),
    ]

    offenders = []
    candidates = [repo_root / "app.py"] + sorted((repo_root / "engine").glob("*.py"))
    for path in candidates:
        if path.name == "store.py":
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in write_patterns:
            if pattern.search(text):
                offenders.append((str(path), pattern.pattern))

    assert offenders == [], f"found direct data-write calls outside store.py: {offenders}"
