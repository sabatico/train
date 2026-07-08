"""Tests for engine/selector.py — the adaptive session-plan builder (ADR-007 rule 5).

Deterministic given its inputs (rng is injected). Built with an in-memory
skills-doc/graph and a fake `words_for` stub so these stay pure-function tests
with no store/IO dependency, per the task brief.
"""
from __future__ import annotations

import random
from datetime import date

import pytest

from engine import config, models, selector


TODAY = date(2026, 7, 10)


def _words(n, prefix="w"):
    return [{"word": f"{prefix}{i}", "phonemes": ["a"]} for i in range(n)]


# ------------------------------------------------------------- scaffold_for
@pytest.mark.parametrize(
    "effective,expected",
    [
        (44, (1, "word_builder")),
        (45, (2, "letter_boxes")),
        (74, (2, "letter_boxes")),
        (75, (3, "echo_dictation")),
        (100, (3, "echo_dictation")),
    ],
)
def test_scaffold_for(effective, expected):
    assert selector.scaffold_for(effective) == expected


def test_scaffold_for_uses_config_constants_boundaries():
    # sanity: the cutoffs used above actually come from config, not hardcoded here
    low_cut, high_cut = config.SCAFFOLD_CUTOFFS
    assert selector.scaffold_for(low_cut - 1)[1] == config.SCAFFOLD_TYPES[0]
    assert selector.scaffold_for(low_cut)[1] == config.SCAFFOLD_TYPES[1]
    assert selector.scaffold_for(high_cut)[1] == config.SCAFFOLD_TYPES[2]


# ------------------------------------------------------------- build_plan
def test_build_plan_returns_n_entries_when_enough_words_n10():
    graph = {"short_vowels": []}
    skills_doc = models.default_skills(graph)
    words = _words(8)

    def words_for(sid):
        return words if sid == "short_vowels" else []

    plan = selector.build_plan(skills_doc, graph, words_for, TODAY, n=10, rng=random.Random(1))
    assert len(plan) == 10


def test_build_plan_returns_n_entries_when_enough_words_n6():
    graph = {"short_vowels": []}
    skills_doc = models.default_skills(graph)
    words = _words(8)

    def words_for(sid):
        return words if sid == "short_vowels" else []

    plan = selector.build_plan(skills_doc, graph, words_for, TODAY, n=6, rng=random.Random(1))
    assert len(plan) == 6


def test_build_plan_empty_when_no_introduced_skill_has_words():
    graph = {"short_vowels": []}
    skills_doc = models.default_skills(graph)

    def no_words(sid):
        return []

    plan = selector.build_plan(skills_doc, graph, no_words, TODAY, n=10, rng=random.Random(1))
    assert plan == []


def test_build_plan_deterministic_under_seeded_rng():
    graph = {"short_vowels": []}
    skills_doc = models.default_skills(graph)
    words = _words(8)

    def words_for(sid):
        return words if sid == "short_vowels" else []

    plan1 = selector.build_plan(skills_doc, graph, words_for, TODAY, n=10, rng=random.Random(99))
    plan2 = selector.build_plan(skills_doc, graph, words_for, TODAY, n=10, rng=random.Random(99))
    assert plan1 == plan2


def test_build_plan_different_seeds_can_differ():
    graph = {"short_vowels": []}
    skills_doc = models.default_skills(graph)
    words = _words(8)

    def words_for(sid):
        return words if sid == "short_vowels" else []

    plan1 = selector.build_plan(skills_doc, graph, words_for, TODAY, n=10, rng=random.Random(1))
    plan2 = selector.build_plan(skills_doc, graph, words_for, TODAY, n=10, rng=random.Random(2))
    # not a strict guarantee for all seeds, but with 8 words and random.choice it's
    # extremely likely the plans differ; if this ever flakes, the seeds can change.
    assert plan1 != plan2


def test_build_plan_focus_slot_targets_weakest_introduced_skill():
    # all 4 no-prereq skills are introduced by default_skills(); pin the other
    # three to high mastery so short_vowels is unambiguously the weakest.
    graph = {"short_vowels": [], "heart_words": [], "letter_orientation": [], "phoneme_segmentation": []}
    skills_doc = models.default_skills(graph)
    skills_doc["skills"]["short_vowels"]["mastery"] = 20
    skills_doc["skills"]["heart_words"]["mastery"] = 90
    skills_doc["skills"]["letter_orientation"]["mastery"] = 90
    skills_doc["skills"]["phoneme_segmentation"]["mastery"] = 90

    def words_for(sid):
        return _words(8, prefix=sid[:2])

    plan = selector.build_plan(skills_doc, graph, words_for, TODAY, n=10, rng=random.Random(3))
    focus_entries = [p for p in plan if p["slot"] == "focus"]
    assert focus_entries, "expected at least one focus-slot entry"
    assert all(p["skill_id"] == "short_vowels" for p in focus_entries)


def test_build_plan_only_introduced_skills_with_words_appear():
    graph = {"short_vowels": [], "heart_words": [], "magic_e": ["short_vowels"]}
    skills_doc = models.default_skills(graph)
    # magic_e is NOT introduced (has a prereq); heart_words has no words available
    all_words = {"short_vowels": _words(8), "heart_words": [], "magic_e": _words(8, prefix="m")}

    def words_for(sid):
        return all_words.get(sid, [])

    plan = selector.build_plan(skills_doc, graph, words_for, TODAY, n=10, rng=random.Random(4))
    skill_ids_used = {p["skill_id"] for p in plan}
    assert "heart_words" not in skill_ids_used  # introduced but no words
    assert "magic_e" not in skill_ids_used  # has words but not introduced
    assert skill_ids_used <= {"short_vowels"}


def test_build_plan_first_warmup_items_are_slot_warmup():
    graph = {"short_vowels": []}
    skills_doc = models.default_skills(graph)
    words = _words(8)

    def words_for(sid):
        return words if sid == "short_vowels" else []

    plan = selector.build_plan(skills_doc, graph, words_for, TODAY, n=10, rng=random.Random(5))
    warmup_count = min(config.WARMUP_ITEMS, 10)
    for entry in plan[:warmup_count]:
        assert entry["slot"] == "warmup"


# ------------------------------------------------------------- _pick_word (helper)
def test_pick_word_reuses_bank_when_all_words_already_used():
    """When every word in the bank is already `used`, _pick_word falls back to
    allowing reuse rather than starving the session (selector.py's documented
    fallback branch)."""
    bank = [{"word": "cat"}]
    used = {"cat"}
    result = selector._pick_word("short_vowels", lambda sid: bank, random.Random(1), used)
    assert result == {"word": "cat"}


def test_pick_word_returns_none_when_bank_is_empty():
    result = selector._pick_word("nothing", lambda sid: [], random.Random(1), set())
    assert result is None


def test_build_plan_via_bootstrapped_student_fixture(bootstrapped_student, data_root):
    """Exercise build_plan against the real seeded word bank / skill graph via
    the store, per the task brief's suggested integration path."""
    from engine import store

    skills_doc = store.load(bootstrapped_student, "skills")
    graph = store.load_skill_graph()

    def words_for(sid):
        return store.load_word_bank(sid)

    plan = selector.build_plan(skills_doc, graph, words_for, TODAY, rng=random.Random(11))
    # short_vowels is introduced at bootstrap and has words in the real seeded bank
    assert len(plan) > 0
    assert all(p["skill_id"] in skills_doc["skills"] for p in plan)


# ------------------------------------------------------------- target_difficulty
@pytest.mark.parametrize(
    "effective,expected",
    [
        (0, 1),
        (100, 5),
        (-1, 1),
        (-50, 1),
        (101, 5),
        (1000, 5),
    ],
)
def test_target_difficulty_boundaries_and_clamping(effective, expected):
    assert selector.target_difficulty(effective) == expected


def test_target_difficulty_monotonic_non_decreasing():
    values = [selector.target_difficulty(m) for m in range(0, 101)]
    assert all(values[i] <= values[i + 1] for i in range(len(values) - 1))


def test_target_difficulty_spans_full_1_to_5_range():
    values = {selector.target_difficulty(m) for m in range(0, 101)}
    assert values == {1, 2, 3, 4, 5}


# ------------------------------------------------------------- _pick_word (target-aware)
def _bank_with_difficulties():
    return [
        {"word": "w1", "difficulty": 1},
        {"word": "w3", "difficulty": 3},
        {"word": "w5", "difficulty": 5},
    ]


def test_pick_word_with_target_picks_closest_difficulty_low():
    bank = _bank_with_difficulties()
    result = selector._pick_word("sid", lambda sid: bank, random.Random(1), set(), target=1)
    assert result["word"] == "w1"


def test_pick_word_with_target_picks_closest_difficulty_high():
    bank = _bank_with_difficulties()
    result = selector._pick_word("sid", lambda sid: bank, random.Random(1), set(), target=5)
    assert result["word"] == "w5"


def test_pick_word_with_target_picks_closest_difficulty_mid():
    bank = _bank_with_difficulties()
    result = selector._pick_word("sid", lambda sid: bank, random.Random(1), set(), target=3)
    assert result["word"] == "w3"


def test_pick_word_target_none_still_returns_a_word_random_path():
    bank = _bank_with_difficulties()
    result = selector._pick_word("sid", lambda sid: bank, random.Random(1), set(), target=None)
    assert result is not None
    assert result["word"] in {"w1", "w3", "w5"}


def test_pick_word_target_aware_still_falls_back_to_reuse_when_exhausted():
    # existing "all words used -> reuse" behavior must still work when a target
    # is supplied, not just in the untargeted path.
    bank = [{"word": "cat", "difficulty": 3}]
    used = {"cat"}
    result = selector._pick_word(
        "short_vowels", lambda sid: bank, random.Random(1), used, target=3
    )
    assert result == {"word": "cat", "difficulty": 3}


def test_pick_word_target_breaks_ties_within_rng_choices():
    # two words equidistant from target=2 (w1 at distance 1, w3 at distance 1);
    # the result must be one of the tied candidates, never w5 (distance 3).
    bank = _bank_with_difficulties()
    result = selector._pick_word("sid", lambda sid: bank, random.Random(7), set(), target=2)
    assert result["word"] in {"w1", "w3"}


# ------------------------------------------------------------- determinism with target-aware picking
def test_build_plan_deterministic_under_seeded_rng_with_difficulty_aware_words():
    # words now carry a "difficulty" field (as real word-bank entries do); confirm
    # target-aware selection didn't break build_plan's determinism guarantee.
    graph = {"short_vowels": []}
    skills_doc = models.default_skills(graph)
    words = [
        {"word": f"w{i}", "phonemes": ["a"], "difficulty": (i % 5) + 1} for i in range(8)
    ]

    def words_for(sid):
        return words if sid == "short_vowels" else []

    plan1 = selector.build_plan(skills_doc, graph, words_for, TODAY, n=10, rng=random.Random(42))
    plan2 = selector.build_plan(skills_doc, graph, words_for, TODAY, n=10, rng=random.Random(42))
    assert plan1 == plan2
