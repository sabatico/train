"""Tests for engine/config.py — pure pedagogy/reward functions (ADR-007/011)."""
from __future__ import annotations

import math

import pytest

from engine import config


# ------------------------------------------------------------- k_for_exposures
def test_k_for_exposures_at_zero_is_base_rate():
    assert config.k_for_exposures(0) == pytest.approx(0.4)


def test_k_for_exposures_monotonically_non_increasing():
    xs = [0, 1, 2, 3, 5, 8, 13, 21, 34, 55, 100, 500]
    ks = [config.k_for_exposures(x) for x in xs]
    for a, b in zip(ks, ks[1:]):
        assert a >= b, f"k_for_exposures should be non-increasing: {ks}"


def test_k_for_exposures_floored_at_min_for_large_exposures():
    k = config.k_for_exposures(1_000_000)
    assert k == pytest.approx(config.EMA_K_MIN)
    # never goes below the floor even further out
    assert config.k_for_exposures(10_000_000) == pytest.approx(config.EMA_K_MIN)


def test_k_for_exposures_never_below_floor():
    for x in range(0, 200, 7):
        assert config.k_for_exposures(x) >= config.EMA_K_MIN - 1e-9


def test_k_for_exposures_matches_formula_before_floor():
    # at exposures == HALFLIFE, K = BASE / 2 (well above the floor)
    expected = config.EMA_K_BASE / 2.0
    assert config.k_for_exposures(int(config.EMA_K_HALFLIFE)) == pytest.approx(expected)
    assert expected > config.EMA_K_MIN  # sanity: this sample point isn't floored


# ------------------------------------------------------------- xp_for_level
def test_xp_for_level_known_values():
    assert config.xp_for_level(1) == 0
    assert config.xp_for_level(2) == 20
    assert config.xp_for_level(3) == 60
    assert config.xp_for_level(4) == 120


def test_xp_for_level_clamps_below_one():
    # n < 1 should behave like level 1 (0 XP needed)
    assert config.xp_for_level(0) == 0
    assert config.xp_for_level(-5) == 0


def test_xp_for_level_strictly_increasing_past_level_1():
    xs = [config.xp_for_level(n) for n in range(1, 10)]
    for a, b in zip(xs, xs[1:]):
        assert b > a


# ------------------------------------------------------------- level_for_xp
def test_level_for_xp_boundaries():
    assert config.level_for_xp(0) == 1
    assert config.level_for_xp(19) == 1
    assert config.level_for_xp(20) == 2
    assert config.level_for_xp(59) == 2
    assert config.level_for_xp(60) == 3
    assert config.level_for_xp(119) == 3
    assert config.level_for_xp(120) == 4


def test_level_for_xp_never_below_one():
    assert config.level_for_xp(-100) == 1


def test_level_for_xp_round_trips_with_xp_for_level():
    for n in range(1, 8):
        threshold = config.xp_for_level(n)
        assert config.level_for_xp(threshold) == n


# ------------------------------------------------------------- level_name
def test_level_name_first_and_last_tier():
    assert config.level_name(1) == config.LEVEL_NAMES[0]
    assert config.level_name(len(config.LEVEL_NAMES)) == config.LEVEL_NAMES[-1]


def test_level_name_bounded_for_very_high_level():
    # must not index past the last tier — this is the "never crash" contract
    huge = len(config.LEVEL_NAMES) + 1000
    assert config.level_name(huge) == config.LEVEL_NAMES[-1]


def test_level_name_all_tiers_reachable_in_order():
    names = [config.level_name(n) for n in range(1, len(config.LEVEL_NAMES) + 1)]
    assert names == list(config.LEVEL_NAMES)


# ------------------------------------------------------------- SKILLS/SKILL_IDS sanity
def test_skill_ids_has_14_entries_matching_skills_dict():
    assert len(config.SKILL_IDS) == 14
    assert set(config.SKILL_IDS) == set(config.SKILLS.keys())


def test_all_decay_rates_are_positive_floats():
    for skill_id, decay in config.SKILLS.items():
        assert isinstance(decay, float)
        assert decay > 0, f"{skill_id} has non-positive decay {decay}"
