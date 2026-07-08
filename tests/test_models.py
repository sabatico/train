"""Tests for engine/models.py — default record factories (ADR-006)."""
from __future__ import annotations

from engine import config, models


# ------------------------------------------------------------- default_profile
def test_default_profile_shape():
    profile = models.default_profile()
    assert profile["display_name"] == "friend"
    assert profile["avatar"] == "panda"
    assert profile["settings"]["tts_voice"] is None
    assert profile["settings"]["tts_rate"] == 0.9
    assert profile["settings"]["font_scale"] == 1.0
    assert profile["settings"]["items_per_session"] == config.ITEMS_PER_SESSION


def test_default_profile_returns_fresh_object_each_call():
    a = models.default_profile()
    b = models.default_profile()
    a["display_name"] = "mutated"
    a["settings"]["tts_rate"] = 999
    assert b["display_name"] == "friend"
    assert b["settings"]["tts_rate"] == 0.9


# ------------------------------------------------------------- default_rewards
def test_default_rewards_shape():
    rewards = models.default_rewards()
    assert rewards["stars_total"] == 0
    assert rewards["xp"] == 0
    assert rewards["level"] == 1
    assert rewards["level_name"] == config.level_name(1)
    assert rewards["streak"] == {"count": 0, "last_day": None, "freezes": 0}
    assert rewards["collection"] == []


def test_default_rewards_returns_fresh_object_each_call():
    a = models.default_rewards()
    b = models.default_rewards()
    a["stars_total"] = 500
    a["collection"].append({"skill_id": "x", "creature_id": "y", "hatched_on": "2026-01-01"})
    a["streak"]["count"] = 30
    assert b["stars_total"] == 0
    assert b["collection"] == []
    assert b["streak"]["count"] == 0


# ------------------------------------------------------------- default_skill
def test_default_skill_introduced_starts_at_initial_mastery():
    skill = models.default_skill("short_vowels", introduced=True)
    assert skill["id"] == "short_vowels"
    assert skill["mastery"] == config.INITIAL_MASTERY
    assert skill["introduced"] is True
    assert skill["last_practiced"] is None
    assert skill["exposures"] == 0
    assert skill["streak"] == 0
    assert skill["decay_per_day"] == config.SKILLS["short_vowels"]


def test_default_skill_not_introduced_starts_at_zero_mastery():
    skill = models.default_skill("magic_e", introduced=False)
    assert skill["mastery"] == 0
    assert skill["introduced"] is False


# ------------------------------------------------------------- default_skills
NO_PREREQ_SKILLS = {"letter_orientation", "phoneme_segmentation", "short_vowels", "heart_words"}


def test_default_skills_has_14_entries():
    graph = {sid: [] for sid in config.SKILL_IDS}
    result = models.default_skills(graph)
    assert set(result["skills"].keys()) == set(config.SKILL_IDS)
    assert len(result["skills"]) == 14


def test_default_skills_introduced_iff_no_prereqs():
    # a graph mirroring the real skill_graph.json shape
    graph = {
        "letter_orientation": [],
        "phoneme_segmentation": [],
        "short_vowels": [],
        "heart_words": [],
        "blends": ["short_vowels"],
        "digraphs": ["short_vowels"],
        "magic_e": ["short_vowels"],
        "r_controlled": ["short_vowels"],
        "suffixes": ["short_vowels"],
        "doubling_endings": ["short_vowels", "blends"],
        "vowel_teams": ["short_vowels", "digraphs"],
        "word_sequencing": ["blends"],
        "phrase_dictation": ["short_vowels", "digraphs"],
        "sentence_writing": ["phrase_dictation"],
    }
    result = models.default_skills(graph)["skills"]
    for skill_id, record in result.items():
        expected_introduced = skill_id in NO_PREREQ_SKILLS
        assert record["introduced"] is expected_introduced, skill_id
        expected_mastery = config.INITIAL_MASTERY if expected_introduced else 0
        assert record["mastery"] == expected_mastery, skill_id


def test_default_skills_with_empty_graph_marks_all_introduced():
    # empty prereqs list (via .get default) => vacuously introduced for every skill
    result = models.default_skills({})["skills"]
    for skill_id, record in result.items():
        assert record["introduced"] is True, skill_id
        assert record["mastery"] == config.INITIAL_MASTERY


def test_default_skills_returns_fresh_object_each_call():
    graph = {sid: [] for sid in config.SKILL_IDS}
    a = models.default_skills(graph)
    b = models.default_skills(graph)
    a["skills"]["short_vowels"]["mastery"] = 999
    assert b["skills"]["short_vowels"]["mastery"] == config.INITIAL_MASTERY
