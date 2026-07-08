"""Tests for engine/skills.py — the mastery model (ADR-007).

Pure functions over skill records; no IO. Built in-memory to match the
skill-record shape from engine/models.py (see default_skill).
"""
from __future__ import annotations

from datetime import date

import pytest

from engine import config, skills


def make_skill(
    *,
    mastery=50,
    last_practiced=None,
    exposures=0,
    streak=0,
    introduced=True,
    decay_per_day=1.0,
):
    return {
        "id": "test_skill",
        "mastery": mastery,
        "last_practiced": last_practiced,
        "exposures": exposures,
        "streak": streak,
        "introduced": introduced,
        "decay_per_day": decay_per_day,
    }


TODAY = date(2026, 7, 10)


# ------------------------------------------------------------- effective_mastery
def test_effective_mastery_no_decay_when_never_practiced():
    s = make_skill(mastery=42, last_practiced=None, decay_per_day=5.0)
    assert skills.effective_mastery(s, TODAY) == 42


def test_effective_mastery_decays_by_decay_per_day_times_elapsed_days():
    s = make_skill(mastery=50, last_practiced="2026-07-05", decay_per_day=2.0)
    # 5 elapsed days * 2.0/day = 10 decay
    assert skills.effective_mastery(s, TODAY) == 40


def test_effective_mastery_is_idempotent_across_repeated_calls():
    """Guards the real compounding-decay bug already fixed (ADR-007 rule 3):
    calling effective_mastery twice for the same `today` must return the same
    value both times (a lazy projection from a fixed baseline, not a mutation)."""
    s = make_skill(mastery=50, last_practiced="2026-07-01", decay_per_day=1.0)
    first = skills.effective_mastery(s, TODAY)
    second = skills.effective_mastery(s, TODAY)
    assert first == second
    # and the stored baseline itself must be untouched
    assert s["mastery"] == 50


def test_effective_mastery_clamps_at_zero():
    s = make_skill(mastery=10, last_practiced="2026-01-01", decay_per_day=5.0)
    assert skills.effective_mastery(s, TODAY) == 0


def test_effective_mastery_days_zero_or_negative_returns_stored_base():
    same_day = make_skill(mastery=33, last_practiced=TODAY.isoformat(), decay_per_day=9.0)
    assert skills.effective_mastery(same_day, TODAY) == 33

    future_practiced = make_skill(mastery=33, last_practiced="2026-07-15", decay_per_day=9.0)
    assert skills.effective_mastery(future_practiced, TODAY) == 33


# ------------------------------------------------------------- score_for
@pytest.mark.parametrize(
    "correct,corrected,expected",
    [
        (True, False, config.SCORE_FIRST_TRY),
        (True, True, config.SCORE_AFTER_CORRECTION),
        (False, False, config.SCORE_MISS),
        (False, True, config.SCORE_MISS),
    ],
)
def test_score_for(correct, corrected, expected):
    assert skills.score_for(correct, corrected) == expected
    assert expected in (1.0, 0.5, 0.0)


# ------------------------------------------------------------- update_mastery
def test_update_mastery_moves_toward_score_and_updates_bookkeeping():
    s = make_skill(mastery=50, last_practiced=None, exposures=0, streak=0)
    result = skills.update_mastery(s, 1.0, TODAY)
    assert result is s  # in place
    k = config.k_for_exposures(0)
    expected = max(0.0, min(100.0, 50 + k * (100.0 - 50)))
    assert s["mastery"] == pytest.approx(expected)
    assert s["last_practiced"] == TODAY.isoformat()
    assert s["exposures"] == 1
    assert s["streak"] == 1


def test_update_mastery_resets_streak_on_non_first_try():
    s = make_skill(mastery=50, streak=4)
    skills.update_mastery(s, 0.5, TODAY)
    assert s["streak"] == 0

    s2 = make_skill(mastery=50, streak=4)
    skills.update_mastery(s2, 0.0, TODAY)
    assert s2["streak"] == 0


def test_update_mastery_streak_increments_only_on_perfect_score():
    s = make_skill(mastery=50, streak=2)
    skills.update_mastery(s, config.SCORE_FIRST_TRY, TODAY)
    assert s["streak"] == 3


def test_update_mastery_learning_rate_slows_as_exposures_grow():
    """Two updates from the same starting mastery with a high score should move
    less the second time once exposures have accrued (K decreases)."""
    low_exposure = make_skill(mastery=50, exposures=0)
    skills.update_mastery(low_exposure, 1.0, TODAY)
    move_1 = low_exposure["mastery"] - 50

    high_exposure = make_skill(mastery=50, exposures=50)
    skills.update_mastery(high_exposure, 1.0, TODAY)
    move_2 = high_exposure["mastery"] - 50

    assert move_2 < move_1


def test_update_mastery_exposures_increments_each_call():
    s = make_skill(mastery=50, exposures=3)
    skills.update_mastery(s, 1.0, TODAY)
    assert s["exposures"] == 4


def test_update_mastery_clamped_to_0_100():
    high = make_skill(mastery=99, exposures=0)
    skills.update_mastery(high, 1.0, TODAY)
    assert 0 <= high["mastery"] <= 100

    low = make_skill(mastery=1, exposures=0)
    skills.update_mastery(low, 0.0, TODAY)
    assert 0 <= low["mastery"] <= 100


def test_update_mastery_starts_from_effective_not_stored_after_decay():
    # stored mastery 80, but 10 days of decay at 2/day -> effective 60
    s = make_skill(mastery=80, last_practiced="2026-06-30", decay_per_day=2.0, exposures=0)
    skills.update_mastery(s, 0.0, TODAY)
    k = config.k_for_exposures(0)
    expected = max(0.0, min(100.0, 60 + k * (0.0 - 60)))
    assert s["mastery"] == pytest.approx(expected)


# ------------------------------------------------------------- is_mastered
def test_is_mastered_true_at_threshold():
    s = make_skill(mastery=config.MASTERY_THRESHOLD, last_practiced=None)
    assert skills.is_mastered(s, TODAY) is True


def test_is_mastered_true_above_threshold():
    s = make_skill(mastery=config.MASTERY_THRESHOLD + 5, last_practiced=None)
    assert skills.is_mastered(s, TODAY) is True


def test_is_mastered_false_just_below_threshold():
    s = make_skill(mastery=config.MASTERY_THRESHOLD - 1, last_practiced=None)
    assert skills.is_mastered(s, TODAY) is False


def test_is_mastered_false_after_decay_pulls_below_threshold():
    # stored mastery just above threshold, but decay pulls effective below it
    s = make_skill(
        mastery=config.MASTERY_THRESHOLD + 1,
        last_practiced="2026-07-09",
        decay_per_day=5.0,
    )
    assert skills.effective_mastery(s, TODAY) < config.MASTERY_THRESHOLD
    assert skills.is_mastered(s, TODAY) is False


# ------------------------------------------------------------- prerequisites_met
def test_prerequisites_met_vacuously_true_when_no_prereqs():
    graph = {"short_vowels": []}
    assert skills.prerequisites_met("short_vowels", {}, graph, TODAY) is True


def test_prerequisites_met_false_when_prereq_below_unlock_threshold():
    graph = {"magic_e": ["short_vowels"]}
    skills_dict = {"short_vowels": make_skill(mastery=config.UNLOCK_THRESHOLD - 1, last_practiced=None)}
    assert skills.prerequisites_met("magic_e", skills_dict, graph, TODAY) is False


def test_prerequisites_met_false_when_prereq_missing_entirely():
    graph = {"magic_e": ["short_vowels"]}
    assert skills.prerequisites_met("magic_e", {}, graph, TODAY) is False


def test_prerequisites_met_true_when_all_prereqs_at_or_above_threshold():
    graph = {"vowel_teams": ["short_vowels", "digraphs"]}
    skills_dict = {
        "short_vowels": make_skill(mastery=config.UNLOCK_THRESHOLD, last_practiced=None),
        "digraphs": make_skill(mastery=config.UNLOCK_THRESHOLD + 10, last_practiced=None),
    }
    assert skills.prerequisites_met("vowel_teams", skills_dict, graph, TODAY) is True


def test_prerequisites_met_uses_effective_mastery_decayed_prereq_fails():
    graph = {"magic_e": ["short_vowels"]}
    # stored mastery is comfortably above threshold, but heavy decay drops it below
    skills_dict = {
        "short_vowels": make_skill(
            mastery=config.UNLOCK_THRESHOLD + 20,
            last_practiced="2026-07-01",
            decay_per_day=10.0,
        )
    }
    assert skills.effective_mastery(skills_dict["short_vowels"], TODAY) < config.UNLOCK_THRESHOLD
    assert skills.prerequisites_met("magic_e", skills_dict, graph, TODAY) is False


# ------------------------------------------------------------- update_introductions
def test_update_introductions_latches_newly_unlockable_skills():
    graph = {"short_vowels": [], "magic_e": ["short_vowels"]}
    skills_doc = {
        "skills": {
            "short_vowels": make_skill(mastery=90, last_practiced=None, introduced=True),
            "magic_e": make_skill(mastery=0, last_practiced=None, introduced=False),
        }
    }
    newly = skills.update_introductions(skills_doc, graph, TODAY)
    assert newly == ["magic_e"]
    assert skills_doc["skills"]["magic_e"]["introduced"] is True


def test_update_introductions_sets_initial_mastery_if_lower():
    graph = {"short_vowels": [], "magic_e": ["short_vowels"]}
    skills_doc = {
        "skills": {
            "short_vowels": make_skill(mastery=90, last_practiced=None, introduced=True),
            "magic_e": make_skill(mastery=0, last_practiced=None, introduced=False),
        }
    }
    skills.update_introductions(skills_doc, graph, TODAY)
    assert skills_doc["skills"]["magic_e"]["mastery"] == config.INITIAL_MASTERY


def test_update_introductions_does_not_lower_mastery_above_initial():
    """If a not-yet-introduced skill somehow already has mastery above
    INITIAL_MASTERY, introducing it must not clobber that value downward."""
    graph = {"short_vowels": [], "magic_e": ["short_vowels"]}
    skills_doc = {
        "skills": {
            "short_vowels": make_skill(mastery=90, last_practiced=None, introduced=True),
            "magic_e": make_skill(mastery=config.INITIAL_MASTERY + 30, last_practiced=None, introduced=False),
        }
    }
    skills.update_introductions(skills_doc, graph, TODAY)
    assert skills_doc["skills"]["magic_e"]["mastery"] == config.INITIAL_MASTERY + 30


def test_update_introductions_does_not_touch_already_introduced_skills():
    graph = {"short_vowels": []}
    skills_doc = {
        "skills": {
            "short_vowels": make_skill(mastery=77, last_practiced=None, introduced=True, exposures=5),
        }
    }
    newly = skills.update_introductions(skills_doc, graph, TODAY)
    assert newly == []
    assert skills_doc["skills"]["short_vowels"]["mastery"] == 77
    assert skills_doc["skills"]["short_vowels"]["exposures"] == 5


def test_update_introductions_skill_with_unmet_prereqs_stays_not_introduced():
    graph = {"short_vowels": [], "magic_e": ["short_vowels"]}
    skills_doc = {
        "skills": {
            "short_vowels": make_skill(mastery=10, last_practiced=None, introduced=True),
            "magic_e": make_skill(mastery=0, last_practiced=None, introduced=False),
        }
    }
    newly = skills.update_introductions(skills_doc, graph, TODAY)
    assert newly == []
    assert skills_doc["skills"]["magic_e"]["introduced"] is False


def test_update_introductions_is_one_way_latch_never_uninitroduces():
    """Even if effective mastery of a prereq later decays below threshold, an
    already-introduced skill must never be un-introduced."""
    graph = {"short_vowels": [], "magic_e": ["short_vowels"]}
    skills_doc = {
        "skills": {
            "short_vowels": make_skill(mastery=10, last_practiced=None, introduced=True),
            "magic_e": make_skill(mastery=50, last_practiced=None, introduced=True),
        }
    }
    newly = skills.update_introductions(skills_doc, graph, TODAY)
    assert newly == []
    assert skills_doc["skills"]["magic_e"]["introduced"] is True
    assert skills_doc["skills"]["magic_e"]["mastery"] == 50  # untouched


# ------------------------------------------------------------- introduced_skills
def test_introduced_skills_returns_only_introduced_ids():
    skills_doc = {
        "skills": {
            "a": make_skill(introduced=True),
            "b": make_skill(introduced=False),
            "c": make_skill(introduced=True),
        }
    }
    assert set(skills.introduced_skills(skills_doc)) == {"a", "c"}


# ------------------------------------------------------------- weakest_introduced
def test_weakest_introduced_none_when_nothing_introduced():
    skills_doc = {"skills": {"a": make_skill(introduced=False, mastery=50)}}
    assert skills.weakest_introduced(skills_doc, TODAY) is None


def test_weakest_introduced_returns_lowest_effective_mastery_skill():
    skills_doc = {
        "skills": {
            "a": make_skill(introduced=True, mastery=80, last_practiced=None),
            "b": make_skill(introduced=True, mastery=30, last_practiced=None),
            "c": make_skill(introduced=True, mastery=55, last_practiced=None),
            "d": make_skill(introduced=False, mastery=1, last_practiced=None),
        }
    }
    assert skills.weakest_introduced(skills_doc, TODAY) == "b"


def test_weakest_introduced_uses_effective_mastery_not_stored():
    # 'a' has a higher stored mastery than 'b' but heavy decay makes it weaker
    skills_doc = {
        "skills": {
            "a": make_skill(introduced=True, mastery=90, last_practiced="2026-07-01", decay_per_day=10.0),
            "b": make_skill(introduced=True, mastery=50, last_practiced=None, decay_per_day=1.0),
        }
    }
    assert skills.effective_mastery(skills_doc["skills"]["a"], TODAY) < skills.effective_mastery(
        skills_doc["skills"]["b"], TODAY
    )
    assert skills.weakest_introduced(skills_doc, TODAY) == "a"
