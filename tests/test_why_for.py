"""Tests for engine/contracts.why_for + _sound_out — the per-word, generated
kid-voice correction/teach explanation (replaces the old static CANNED_WHY dict).

why_for(skill_id, word_entry) -> (rule_id, text). Decodable patterns get a
sound-by-sound blend built from the word's phonemes; heart words and magic_e
get a different (non-sound-out) explanation. See engine/contracts.py for the
design notes.
"""
from __future__ import annotations

from engine import contracts


# --------------------------------------------------------------- _sound_out
def test_sound_out_formats_each_phoneme_in_slashes():
    assert contracts._sound_out(["p", "u", "p"]) == "/p/ /u/ /p/"


def test_sound_out_empty_list_is_empty_string():
    assert contracts._sound_out([]) == ""


def test_sound_out_single_phoneme():
    assert contracts._sound_out(["a"]) == "/a/"


def test_sound_out_multi_letter_phoneme():
    assert contracts._sound_out(["sh", "i", "p"]) == "/sh/ /i/ /p/"


# --------------------------------------------------------------- short_vowels (default sound-out)
def test_why_for_short_vowels_pup():
    rule_id, text = contracts.why_for("short_vowels", {"word": "pup", "phonemes": ["p", "u", "p"]})
    assert rule_id == "sound_it_out"
    assert text == "Sound out each letter: /p/ /u/ /p/ → pup."


# --------------------------------------------------------------- blends
def test_why_for_blends_stop():
    rule_id, text = contracts.why_for(
        "blends", {"word": "stop", "phonemes": ["s", "t", "o", "p"]}
    )
    assert rule_id == "blend_sounds"
    assert text.startswith("Blend each sound:")
    assert "/s/ /t/ /o/ /p/" in text
    assert text.endswith("→ stop.")


# --------------------------------------------------------------- digraphs
def test_why_for_digraphs_ship():
    rule_id, text = contracts.why_for("digraphs", {"word": "ship", "phonemes": ["sh", "i", "p"]})
    assert rule_id == "digraph_one_sound"
    assert "/sh/ /i/ /p/" in text
    assert "→ ship." in text


# --------------------------------------------------------------- magic_e
def test_why_for_magic_e_hope():
    rule_id, text = contracts.why_for(
        "magic_e", {"word": "hope", "phonemes": ["h", "o", "p", "e"]}
    )
    assert rule_id == "magic_e_silent"
    assert "hope" in text
    assert "say its name" in text


def test_why_for_magic_e_is_not_sound_out_letter_by_letter():
    # magic_e explains the RULE, not a phoneme-by-phoneme blend -> no "/h/ /o/" style markup
    rule_id, text = contracts.why_for(
        "magic_e", {"word": "hope", "phonemes": ["h", "o", "p", "e"]}
    )
    assert "/h/" not in text
    assert "/o/" not in text


# --------------------------------------------------------------- vowel_teams
def test_why_for_vowel_teams_boat():
    rule_id, text = contracts.why_for(
        "vowel_teams", {"word": "boat", "phonemes": ["b", "oa", "t"]}
    )
    assert rule_id == "vowel_team_one_sound"
    assert "/b/ /oa/ /t/" in text
    assert "→ boat." in text


# --------------------------------------------------------------- r_controlled
def test_why_for_r_controlled_car():
    rule_id, text = contracts.why_for("r_controlled", {"word": "car", "phonemes": ["c", "ar"]})
    assert rule_id == "r_controlled"
    assert "/c/ /ar/" in text
    assert "→ car." in text


# --------------------------------------------------------------- heart_words
def test_why_for_heart_words_love():
    rule_id, text = contracts.why_for("heart_words", {"word": "love", "phonemes": ["l", "u", "v"]})
    assert rule_id == "heart_word_by_heart"
    assert "love" in text
    assert "heart" in text
    assert "❤️" in text


def test_why_for_heart_words_has_no_sound_out_arrow():
    # heart words are learned whole, not blended -> no "→" sound-out marker
    rule_id, text = contracts.why_for("heart_words", {"word": "love", "phonemes": ["l", "u", "v"]})
    assert "→" not in text


# --------------------------------------------------------------- doubling_endings / suffixes
def test_why_for_doubling_endings_uses_blend_sounds():
    rule_id, text = contracts.why_for(
        "doubling_endings", {"word": "running", "phonemes": ["r", "u", "n", "n", "i", "ng"]}
    )
    assert rule_id == "blend_sounds"
    assert "→ running." in text


def test_why_for_suffixes_uses_blend_sounds():
    rule_id, text = contracts.why_for(
        "suffixes", {"word": "jumping", "phonemes": ["j", "u", "m", "p", "i", "ng"]}
    )
    assert rule_id == "blend_sounds"
    assert "→ jumping." in text


# --------------------------------------------------------------- unknown skill falls through
def test_why_for_unknown_skill_falls_back_to_sound_it_out():
    rule_id, text = contracts.why_for(
        "word_sequencing", {"word": "cat", "phonemes": ["c", "a", "t"]}
    )
    assert rule_id == "sound_it_out"
    assert text.startswith("Sound out each letter:")


# --------------------------------------------------------------- fallback: no phonemes key
def test_why_for_missing_phonemes_uses_letters_and_does_not_crash():
    rule_id, text = contracts.why_for("short_vowels", {"word": "cat"})
    assert rule_id == "sound_it_out"
    assert text  # non-empty
    assert "cat" in text
    assert text == "Sound out each letter: /c/ /a/ /t/ → cat."


def test_why_for_missing_phonemes_heart_word_still_works():
    # heart_words path doesn't touch `sounds` for its text, but phonemes fallback
    # must still not crash when the key is absent.
    rule_id, text = contracts.why_for("heart_words", {"word": "said"})
    assert rule_id == "heart_word_by_heart"
    assert "said" in text


# --------------------------------------------------------------- integration with build_item
def test_build_item_why_text_fallback_matches_why_for_sound_out():
    item = contracts.build_item(
        "letter_boxes", "short_vowels", {"word": "lap", "phonemes": ["l", "a", "p"]}, 2
    )
    _, expected_text = contracts.why_for(
        "short_vowels", {"word": "lap", "phonemes": ["l", "a", "p"]}
    )
    assert item["why"]["text_fallback"] == expected_text
    assert item["why"]["text_fallback"] == "Sound out each letter: /l/ /a/ /p/ → lap."
