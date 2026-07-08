"""Tests for engine/rewards.py — the gamification economy (ADR-011).

The load-bearing invariant (#3): rewards are only ever ADDED to. Covers
stars_for, add_stars, the streak/freeze state machine, creature hatching, and
a fuzz test asserting monotonic non-decrease across a random sequence of
session-end-style operations.
"""
from __future__ import annotations

import random
from datetime import date, timedelta

import pytest

from engine import config, models, rewards


TODAY = date(2026, 7, 10)


# ------------------------------------------------------------- stars_for
@pytest.mark.parametrize(
    "correct,corrected,expected",
    [
        (True, False, config.STARS_FIRST_TRY),
        (True, True, config.STARS_AFTER_CORRECTION),
        (False, False, 0),
        (False, True, 0),
    ],
)
def test_stars_for(correct, corrected, expected):
    assert rewards.stars_for(correct, corrected) == expected


def test_stars_for_matches_expected_literal_values():
    assert rewards.stars_for(True, False) == 2
    assert rewards.stars_for(True, True) == 1
    assert rewards.stars_for(False, False) == 0


# ------------------------------------------------------------- add_stars
def test_add_stars_increments_stars_total_and_sets_xp_equal():
    r = models.default_rewards()
    rewards.add_stars(r, 5)
    assert r["stars_total"] == 5
    assert r["xp"] == 5


def test_add_stars_accumulates_across_calls():
    r = models.default_rewards()
    rewards.add_stars(r, 5)
    rewards.add_stars(r, 3)
    assert r["stars_total"] == 8
    assert r["xp"] == 8


def test_add_stars_recomputes_level_and_level_name_via_config():
    r = models.default_rewards()
    rewards.add_stars(r, config.xp_for_level(3))  # exactly enough for level 3
    assert r["level"] == config.level_for_xp(r["xp"])
    assert r["level_name"] == config.level_name(r["level"])


def test_add_stars_raises_value_error_on_negative_amount():
    r = models.default_rewards()
    with pytest.raises(ValueError):
        rewards.add_stars(r, -1)


def test_add_stars_zero_is_allowed_and_is_a_noop_on_totals():
    r = models.default_rewards()
    rewards.add_stars(r, 5)
    before = dict(r)
    rewards.add_stars(r, 0)
    assert r["stars_total"] == before["stars_total"]
    assert r["xp"] == before["xp"]


def test_add_stars_negative_amount_does_not_mutate_rewards():
    r = models.default_rewards()
    rewards.add_stars(r, 5)
    snapshot = dict(r)
    with pytest.raises(ValueError):
        rewards.add_stars(r, -10)
    assert r["stars_total"] == snapshot["stars_total"]


# ------------------------------------------------------------- _bump_streak
def test_bump_streak_first_ever_session_sets_count_1():
    r = models.default_rewards()
    rewards._bump_streak(r, TODAY)
    assert r["streak"]["count"] == 1
    assert r["streak"]["last_day"] == TODAY.isoformat()


def test_bump_streak_consecutive_day_increments():
    r = models.default_rewards()
    rewards._bump_streak(r, TODAY)
    rewards._bump_streak(r, TODAY + timedelta(days=1))
    assert r["streak"]["count"] == 2


def test_bump_streak_same_day_second_call_is_noop():
    r = models.default_rewards()
    rewards._bump_streak(r, TODAY)
    rewards._bump_streak(r, TODAY)
    assert r["streak"]["count"] == 1


def test_bump_streak_one_day_gap_with_freeze_spends_it_and_increments():
    r = models.default_rewards()
    r["streak"] = {"count": 3, "last_day": TODAY.isoformat(), "freezes": 1}
    rewards._bump_streak(r, TODAY + timedelta(days=2))  # gap of 1 missed day
    assert r["streak"]["count"] == 4
    assert r["streak"]["freezes"] == 0


def test_bump_streak_multi_day_gap_no_freeze_resets_to_1():
    r = models.default_rewards()
    r["streak"] = {"count": 5, "last_day": TODAY.isoformat(), "freezes": 0}
    rewards._bump_streak(r, TODAY + timedelta(days=4))  # 3 missed days, no freeze
    assert r["streak"]["count"] == 1


def test_bump_streak_earns_freeze_at_multiple_of_5_capped_at_2():
    r = models.default_rewards()
    r["streak"] = {"count": 4, "last_day": TODAY.isoformat(), "freezes": 0}
    rewards._bump_streak(r, TODAY + timedelta(days=1))  # count -> 5
    assert r["streak"]["count"] == 5
    assert r["streak"]["freezes"] == 1


def test_bump_streak_freeze_cap_never_exceeds_2():
    r = models.default_rewards()
    r["streak"] = {"count": 9, "last_day": TODAY.isoformat(), "freezes": 2}
    rewards._bump_streak(r, TODAY + timedelta(days=1))  # count -> 10, multiple of 5
    assert r["streak"]["freezes"] == 2  # already capped, stays capped


def test_bump_streak_via_apply_session_end():
    r = models.default_rewards()
    skills_doc = {"skills": {}}
    rewards.apply_session_end(r, skills_doc, {}, TODAY)
    assert r["streak"]["count"] == 1


# ------------------------------------------------------------- hatch_creatures
def test_hatch_creatures_hatches_when_sustained_above_threshold():
    skills_doc = {
        "skills": {
            "short_vowels": {"mastery": 90, "last_practiced": None, "decay_per_day": 1.0}
        }
    }
    r = models.default_rewards()
    hatched = rewards.hatch_creatures(
        r, skills_doc, {"short_vowels": config.MASTERY_THRESHOLD}, TODAY
    )
    assert hatched == ["short_vowels"]
    assert any(c["skill_id"] == "short_vowels" for c in r["collection"])


def test_hatch_creatures_requires_previous_masteries_also_above_threshold():
    skills_doc = {
        "skills": {
            "short_vowels": {"mastery": 90, "last_practiced": None, "decay_per_day": 1.0}
        }
    }
    r = models.default_rewards()
    hatched = rewards.hatch_creatures(r, skills_doc, {"short_vowels": 50}, TODAY)
    assert hatched == []
    assert r["collection"] == []


def test_hatch_creatures_no_double_hatch_already_in_collection():
    skills_doc = {
        "skills": {
            "short_vowels": {"mastery": 90, "last_practiced": None, "decay_per_day": 1.0}
        }
    }
    r = models.default_rewards()
    rewards.hatch_creatures(r, skills_doc, {"short_vowels": 90}, TODAY)
    assert len(r["collection"]) == 1
    hatched_again = rewards.hatch_creatures(r, skills_doc, {"short_vowels": 90}, TODAY + timedelta(days=1))
    assert hatched_again == []
    assert len(r["collection"]) == 1


def test_hatch_creatures_never_removes_a_hatched_creature_even_after_decay():
    skills_doc = {
        "skills": {
            "short_vowels": {"mastery": 90, "last_practiced": None, "decay_per_day": 1.0}
        }
    }
    r = models.default_rewards()
    rewards.hatch_creatures(r, skills_doc, {"short_vowels": 90}, TODAY)
    assert len(r["collection"]) == 1

    # simulate heavy decay dropping effective mastery well below threshold later
    skills_doc["skills"]["short_vowels"]["last_practiced"] = TODAY.isoformat()
    skills_doc["skills"]["short_vowels"]["decay_per_day"] = 50.0
    later = TODAY + timedelta(days=5)
    rewards.hatch_creatures(r, skills_doc, {"short_vowels": 0}, later)
    assert len(r["collection"]) == 1  # still there, never removed


def test_hatch_creatures_returns_multiple_hatched_ids():
    skills_doc = {
        "skills": {
            "a": {"mastery": 90, "last_practiced": None, "decay_per_day": 1.0},
            "b": {"mastery": 88, "last_practiced": None, "decay_per_day": 1.0},
        }
    }
    r = models.default_rewards()
    hatched = rewards.hatch_creatures(r, skills_doc, {"a": 90, "b": 90}, TODAY)
    assert set(hatched) == {"a", "b"}


# ------------------------------------------------------------- monotonic property (fuzz)
def test_add_stars_is_monotonic_non_decreasing_fuzz():
    """Invariant #3: apply a random sequence of non-negative add_stars amounts
    and assert stars_total/xp/level never decrease from one step to the next."""
    rng = random.Random(2026)
    r = models.default_rewards()
    prev_stars, prev_xp, prev_level = r["stars_total"], r["xp"], r["level"]
    for _ in range(200):
        amount = rng.randint(0, 10)
        rewards.add_stars(r, amount)
        assert r["stars_total"] >= prev_stars
        assert r["xp"] >= prev_xp
        assert r["level"] >= prev_level
        prev_stars, prev_xp, prev_level = r["stars_total"], r["xp"], r["level"]


def test_apply_session_end_is_monotonic_fuzz():
    """Fuzz across many simulated session-ends (varying day gaps and masteries):
    streak count/freezes and collection size must never make rewards 'worse' in
    a way that loses previously earned state -- collection never shrinks."""
    rng = random.Random(7)
    r = models.default_rewards()
    skills_doc = {
        "skills": {
            "short_vowels": {"mastery": 20, "last_practiced": None, "decay_per_day": 0.6}
        }
    }
    day = TODAY
    prev_collection_size = 0
    prev_freezes_seen_max = 0
    for _ in range(50):
        gap = rng.randint(0, 3)
        day = day + timedelta(days=gap)
        mastery_now = rng.randint(0, 100)
        skills_doc["skills"]["short_vowels"]["mastery"] = mastery_now
        skills_doc["skills"]["short_vowels"]["last_practiced"] = day.isoformat()
        previous = {"short_vowels": rng.randint(0, 100)}
        rewards.apply_session_end(r, skills_doc, previous, day)
        assert len(r["collection"]) >= prev_collection_size
        prev_collection_size = len(r["collection"])
