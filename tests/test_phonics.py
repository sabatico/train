"""Tests for engine/phonics.py — grapheme segmentation + word difficulty scoring.

Pure, dependency-free module (PLAN §2). segment_graphemes() defines the sound-box
units word_builder/letter_boxes draw on screen; difficulty() feeds the selector's
difficulty-aware word choice (engine/selector.py::target_difficulty/_pick_word).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from engine import phonics


# ------------------------------------------------------------- segment_graphemes
@pytest.mark.parametrize(
    "word,expected",
    [
        ("cat", ["c", "a", "t"]),
        ("ship", ["sh", "i", "p"]),
        ("boat", ["b", "oa", "t"]),
        ("car", ["c", "ar"]),
        ("night", ["n", "igh", "t"]),
        ("bright", ["b", "r", "igh", "t"]),
        ("hope", ["h", "o", "p", "e"]),  # silent split-e stays a single letter
        ("duck", ["d", "u", "ck"]),
        ("ball", ["b", "a", "ll"]),
        ("rain", ["r", "ai", "n"]),
    ],
)
def test_segment_graphemes_exact(word, expected):
    assert phonics.segment_graphemes(word) == expected


@pytest.mark.parametrize(
    "word",
    [
        "cat", "ship", "boat", "car", "night", "bright", "hope", "duck", "ball",
        "rain", "a", "i", "the", "straight", "eerie", "squirrel", "phone", "gnome",
        "wrist", "knight", "quick", "buzz", "chess", "author", "royal", "chewy",
        "argue", "ruin",
    ],
)
def test_segment_graphemes_joins_back_to_original(word):
    assert "".join(phonics.segment_graphemes(word)) == word


@pytest.mark.parametrize(
    "word",
    ["cat", "ship", "boat", "night", "bright", "a", "the", "straight"],
)
def test_segment_graphemes_all_segments_non_empty(word):
    segments = phonics.segment_graphemes(word)
    assert all(len(s) > 0 for s in segments)


def test_segment_graphemes_longest_match_first_igh():
    # "igh" must be matched as one trigraph unit, never split into "i" + "gh"
    # (or any other partial combination).
    segments = phonics.segment_graphemes("night")
    assert "igh" in segments
    assert "i" not in segments
    assert "gh" not in segments


def test_segment_graphemes_longest_match_first_generic():
    # every multi-letter grapheme present in _GRAPHEMES_SORTED must appear intact
    # (not fragmented) when it's the longest match available at that position.
    segments = phonics.segment_graphemes("bright")
    assert segments == ["b", "r", "igh", "t"]
    # sanity: "r" + "igh" are separate segments, not merged or split further
    assert "r" in segments


def test_segment_graphemes_single_letter():
    assert phonics.segment_graphemes("a") == ["a"]
    assert phonics.segment_graphemes("i") == ["i"]


def test_segment_graphemes_empty_string_no_error():
    assert phonics.segment_graphemes("") == []


def test_segment_graphemes_is_case_insensitive_lowercases_output():
    assert phonics.segment_graphemes("CAT") == ["c", "a", "t"]
    assert phonics.segment_graphemes("Night") == ["n", "igh", "t"]


def test_segment_graphemes_digraph_sh():
    assert phonics.segment_graphemes("fish") == ["f", "i", "sh"]


def test_segment_graphemes_r_controlled_er():
    assert phonics.segment_graphemes("her") == ["h", "er"]


def test_segment_graphemes_double_consonant():
    # "zz" is in _GRAPHEMES (doubles); "gg" is not, so "egg" segments letter-by-letter.
    assert phonics.segment_graphemes("buzz") == ["b", "u", "zz"]
    assert phonics.segment_graphemes("egg") == ["e", "g", "g"]


# ------------------------------------------------------------- difficulty
@pytest.mark.parametrize(
    "word,pattern",
    [
        ("cat", "short_vowels"),
        ("ship", "digraphs"),
        ("boat", "vowel_teams"),
        ("bright", "vowel_teams"),
        ("straight", "vowel_teams"),
        ("her", "r_controlled"),
        ("jumping", "suffixes"),
        ("a", "short_vowels"),
        ("unknownpattern", "not_a_real_pattern"),
    ],
)
def test_difficulty_returns_int_in_range(word, pattern):
    d = phonics.difficulty(word, pattern)
    assert isinstance(d, int)
    assert 1 <= d <= 5


def test_difficulty_common_short_cvc_easier_than_long_multigrapheme_word():
    easy = phonics.difficulty("cat", "short_vowels")
    hard = phonics.difficulty("bright", "vowel_teams")
    harder = phonics.difficulty("straight", "vowel_teams")
    assert easy < hard
    assert easy < harder


def test_difficulty_higher_pattern_base_scores_gte_lower_base_same_word():
    # _PATTERN_BASE: vowel_teams (3) > short_vowels (1) for the identical word "cat"
    low_base_score = phonics.difficulty("cat", "short_vowels")
    high_base_score = phonics.difficulty("cat", "vowel_teams")
    assert phonics._PATTERN_BASE["vowel_teams"] > phonics._PATTERN_BASE["short_vowels"]
    assert high_base_score >= low_base_score


def test_difficulty_pattern_base_ordering_holds_for_all_pairs():
    # generic property: for any two patterns, whichever has the higher _PATTERN_BASE
    # should never score lower for the same word (all else equal), unless clamping
    # at the 1..5 boundary hides the difference.
    word = "van"  # short, not in _COMMON, single-letter phonemes only
    scores = {p: phonics.difficulty(word, p) for p in phonics._PATTERN_BASE}
    for p1 in phonics._PATTERN_BASE:
        for p2 in phonics._PATTERN_BASE:
            if phonics._PATTERN_BASE[p1] > phonics._PATTERN_BASE[p2]:
                assert scores[p1] >= scores[p2], (p1, p2)


def test_difficulty_common_word_gets_nudge_down_vs_noncommon_same_shape():
    # "at" is in _COMMON, "cat" is not; both are short, single-syllable, simple
    # single-letter-phoneme words. Using pattern "vowel_teams" (base=3, not
    # clamped at the floor) makes the -1 nudge visible.
    assert "at" in phonics._COMMON
    assert "cat" not in phonics._COMMON
    common_score = phonics.difficulty("at", "vowel_teams")
    noncommon_score = phonics.difficulty("cat", "vowel_teams")
    assert common_score < noncommon_score


def test_difficulty_explicit_phonemes_respected_multiletter_raises_score():
    # same word/pattern, but explicit phonemes with a multi-letter grapheme should
    # score >= the single-letter-phoneme version (the multi-letter-grapheme +1).
    single_letter_score = phonics.difficulty("ab", "short_vowels", phonemes=["a", "b"])
    multiletter_score = phonics.difficulty("ab", "short_vowels", phonemes=["ab"])
    assert multiletter_score > single_letter_score


def test_difficulty_explicit_phonemes_override_segmentation():
    # passing phonemes bypasses segment_graphemes() entirely; giving 4+ "phonemes"
    # for a short word should raise the score via the len(ph) >= 4 rule, even
    # though segment_graphemes("abc") would give fewer segments.
    default_score = phonics.difficulty("abc", "short_vowels")
    inflated_score = phonics.difficulty(
        "abc", "short_vowels", phonemes=["a", "b", "c", "d"]
    )
    assert inflated_score >= default_score


def test_difficulty_clamped_to_1_through_5_even_for_extreme_inputs():
    # a pattern not in _PATTERN_BASE defaults to base 2; stack every score-raising
    # factor to try to exceed 5, and confirm the clamp holds.
    d = phonics.difficulty(
        "supercalifragilisticexpialidocious",
        "vowel_teams",
        phonemes=["su", "per", "cal", "if", "rag", "il", "ist", "ic"],
    )
    assert 1 <= d <= 5


def test_difficulty_deterministic_same_inputs_same_output():
    a = phonics.difficulty("night", "vowel_teams")
    b = phonics.difficulty("night", "vowel_teams")
    assert a == b
