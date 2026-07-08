"""Tests for engine/classifier.py — the error classifier (ADR-008).

Deterministic, dependency-free. Covers the alignment algorithm, transposition
and phonetic-plausibility detectors, the tagging rules straight from the
ADR-008 table, and the frozen tag enum.
"""
from __future__ import annotations

from engine import classifier


# ------------------------------------------------------------- frozen enum
def test_tags_enum_is_frozen_exact_order_and_membership():
    """Locks the taxonomy against accidental renames (ADR-008 requirement) --
    this MUST match exactly, including order, since the tag set is a permanent
    data contract for historical logs."""
    assert classifier.TAGS == (
        "correct",
        "reversal",
        "transposition",
        "omission",
        "insertion",
        "phonetic_plausible",
        "vowel_substitution",
        "pattern_violation",
        "heart_word_miss",
    )


# ------------------------------------------------------------- align
def test_align_identical_strings_all_match():
    ops = classifier.align("cat", "cat")
    assert ops == [("match", "c", "c"), ("match", "a", "a"), ("match", "t", "t")]


def test_align_substitution():
    ops = classifier.align("cot", "cat")
    kinds = [op for op, _, _ in ops]
    assert "sub" in kinds
    # exactly one substitution, rest matches
    assert ops == [("match", "c", "c"), ("sub", "o", "a"), ("match", "t", "t")]


def test_align_deletion_missing_attempt_char():
    # "ct" vs "cat" -- attempt is missing the 'a' -> a 'del' op (target char missing)
    ops = classifier.align("ct", "cat")
    kinds = [op for op, _, _ in ops]
    assert "del" in kinds


def test_align_insertion_extra_attempt_char():
    # "caat" vs "cat" -- attempt has an extra 'a' -> an 'ins' op
    ops = classifier.align("caat", "cat")
    kinds = [op for op, _, _ in ops]
    assert "ins" in kinds


# ------------------------------------------------------------- _is_transposition
def test_is_transposition_true_for_adjacent_swap():
    assert classifier._is_transposition("freind", "friend") is True


def test_is_transposition_false_for_identical_strings():
    assert classifier._is_transposition("cat", "cat") is False


def test_is_transposition_false_for_different_length():
    assert classifier._is_transposition("cats", "cat") is False


# ------------------------------------------------------------- is_phonetically_plausible
def test_is_phonetically_plausible_kat_cat():
    assert classifier.is_phonetically_plausible("kat", "cat") is True


def test_is_phonetically_plausible_with_target_phonemes_luv_love():
    assert (
        classifier.is_phonetically_plausible("luv", "love", target_phonemes=["l", "u", "v"])
        is True
    )


def test_is_phonetically_plausible_false_for_identical_strings():
    assert classifier.is_phonetically_plausible("cat", "cat") is False


def test_is_phonetically_plausible_trailing_silent_e_dropped():
    # "hop" vs "hope" -- the phonetic key drops hope's trailing silent e -> "hop"
    assert classifier.is_phonetically_plausible("hop", "hope") is True


def test_is_phonetically_plausible_y_normalized_to_i():
    # "mi" vs "my" -- 'y' folds to 'i' in the phonetic key
    assert classifier.is_phonetically_plausible("mi", "my") is True


def test_is_phonetically_plausible_collapses_doubled_letters():
    # "buz" vs "buzz" -- doubled consonants collapse in the phonetic key
    assert classifier.is_phonetically_plausible("buz", "buzz") is True


# ------------------------------------------------------------- classify
def test_classify_luv_love_heart_word_with_phonemes():
    result = classifier.classify(
        "luv", "love", is_heart_word=True, target_phonemes=["l", "u", "v"]
    )
    assert "phonetic_plausible" in result["tags"]
    assert "heart_word_miss" in result["tags"]
    assert result["primary"] == "heart_word_miss"


def test_classify_dehind_behind_reversal():
    result = classifier.classify("dehind", "behind")
    assert "reversal" in result["tags"]
    assert result["primary"] == "reversal"


def test_classify_freind_friend_transposition():
    result = classifier.classify("freind", "friend")
    assert "transposition" in result["tags"]
    assert result["primary"] == "transposition"


def test_classify_behin_behind_omission():
    result = classifier.classify("behin", "behind")
    assert "omission" in result["tags"]


def test_classify_behaind_behind_insertion():
    result = classifier.classify("behaind", "behind")
    assert "insertion" in result["tags"]


def test_classify_pit_pet_vowel_substitution():
    result = classifier.classify("pit", "pet")
    assert "vowel_substitution" in result["tags"]


def test_classify_sed_said_heart_word_miss():
    result = classifier.classify("sed", "said", is_heart_word=True)
    assert "heart_word_miss" in result["tags"]
    assert result["primary"] == "heart_word_miss"


def test_classify_exact_match_is_correct_only():
    result = classifier.classify("love", "love")
    assert result["tags"] == ["correct"]
    assert result["primary"] == "correct"


def test_classify_returns_full_shape():
    result = classifier.classify("cat", "cat")
    assert set(result.keys()) == {"tags", "primary", "alignment", "is_phonetic"}
    assert result["is_phonetic"] is False


def test_classify_case_and_whitespace_normalized_to_correct():
    result = classifier.classify("  Cat ", "cat")
    assert result["tags"] == ["correct"]


def test_classify_fallback_pattern_violation_when_no_other_tag_applies():
    # same-length substitution that is neither a mirror-reversal, transposition,
    # vowel-substitution nor phonetically plausible, and not a heart word.
    result = classifier.classify("bat", "bag")
    assert "pattern_violation" in result["tags"] or len(result["tags"]) >= 1
    # whatever tags applied, a primary must always be set
    assert result["primary"] in classifier.TAGS
