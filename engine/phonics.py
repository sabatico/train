"""Phonics utilities — grapheme segmentation + a difficulty score (PLAN §2).

Pure, deterministic, dependency-free. Two jobs used when building/validating word
banks (and later when validating AI-generated words):
  * segment_graphemes(word): split a word into its grapheme units (sound spellings)
    so word_builder draws one sound box per unit and letter_boxes groups digraphs.
  * difficulty(...): a 1–5 complexity score so the selector can order words
    easy→hard within a skill (answers "which word is harder?").
"""
from __future__ import annotations

# Multi-letter graphemes, matched LONGEST-FIRST at each position. Order matters:
# trigraphs before digraphs before single letters.
_GRAPHEMES = (
    # trigraphs / r+e and vowel-r-e
    "igh", "tch", "dge", "air", "ear", "are", "ore", "oor", "our", "eer",
    # consonant digraphs
    "sh", "ch", "th", "wh", "ck", "ph", "ng", "qu", "wr", "kn", "gn",
    # vowel teams / diphthongs
    "ai", "ay", "ea", "ee", "ey", "ie", "oa", "oe", "oo", "ou", "ow",
    "oi", "oy", "au", "aw", "ew", "ue", "ui",
    # r-controlled (vowel + r as one unit)
    "ar", "or", "er", "ir", "ur",
    # doubles
    "ll", "ss", "ff", "zz",
)
# sorted so the matcher always tries the longest candidate first
_GRAPHEMES_SORTED = tuple(sorted(_GRAPHEMES, key=len, reverse=True))

# A small high-frequency set (Fry first ~100) — common words score easier.
_COMMON = frozenset(
    "a about all am an and are as at be but by can come day did do down each find "
    "first for from get go had has have he her him his how i if in into is it like "
    "long look made make many may more my no not now of on one or out see she so "
    "some the their them then there they this time to two up use was we were what "
    "when who will with you your".split()
)


def segment_graphemes(word: str) -> list[str]:
    """Split a lowercase word into grapheme units, longest-match-first.

    'ship'→['sh','i','p']; 'boat'→['b','oa','t']; 'car'→['c','ar'];
    'night'→['n','igh','t']; 'hope'→['h','o','p','e'] (a silent split-e stays a
    single letter — good enough for spelling practice)."""
    w = word.lower()
    out: list[str] = []
    i = 0
    n = len(w)
    while i < n:
        for g in _GRAPHEMES_SORTED:
            if w.startswith(g, i):
                out.append(g)
                i += len(g)
                break
        else:
            out.append(w[i])
            i += 1
    return out


# per-skill base difficulty (the between-pattern ordering, ADR-007 scope & sequence)
_PATTERN_BASE = {
    "short_vowels": 1,
    "heart_words": 2,
    "digraphs": 2,
    "magic_e": 2,
    "blends": 2,
    "doubling_endings": 2,
    "suffixes": 3,
    "r_controlled": 3,
    "vowel_teams": 3,
    "word_sequencing": 3,
}


def difficulty(word: str, pattern: str, phonemes: list[str] | None = None) -> int:
    """A 1–5 complexity score. Combines the pattern's place in the scope & sequence
    with per-word factors: length, grapheme count, multi-letter graphemes, and
    whether it's a very common word (easier)."""
    w = word.lower()
    ph = phonemes if phonemes is not None else segment_graphemes(w)
    score = _PATTERN_BASE.get(pattern, 2)
    if len(w) >= 5:
        score += 1
    if len(ph) >= 4:
        score += 1
    if any(len(g) > 1 for g in ph):
        score += 1
    if w in _COMMON:
        score -= 1
    return max(1, min(5, score))
