"""Tests for engine/contracts.py — the ADR-005 exercise item contract.

Covers the envelope builder, per-type payloads, validation, public_item
(answer-key stripping), phoneme helpers, and the agent tool/json schemas.
"""
from __future__ import annotations

import copy

import pytest

from engine import contracts

SHIP = {
    "word": "ship",
    "phonemes": ["sh", "i", "p"],
    "pattern": "digraphs",
    "tricky_letters": [],
    "emoji": "🚢",
    "distractors": ["c", "e"],
}
CAT = {
    "word": "cat",
    "phonemes": ["c", "a", "t"],
    "pattern": "short_vowels",
    "tricky_letters": [],
    "emoji": "🐱",
    "distractors": ["k", "e"],
}
LOVE = {
    "word": "love",
    "phonemes": ["l", "u", "v"],
    "pattern": "heart_words",
    "tricky_letters": [1, 3],
    "emoji": "❤️",
    "distractors": [],
}


# --------------------------------------------------------------- build_item / envelope
@pytest.mark.parametrize("ex_type", contracts.EXERCISE_TYPES)
def test_build_item_valid_for_each_type(ex_type):
    item = contracts.build_item(ex_type, "short_vowels", CAT, 1)
    assert contracts.validate_item(item) is True
    assert item["contract_version"] == 1
    assert isinstance(item["item_id"], str) and item["item_id"]
    assert item["target"] == "cat"
    assert item["type"] == ex_type


def test_build_item_unknown_type_raises():
    with pytest.raises(ValueError):
        contracts.build_item("bogus_type", "short_vowels", CAT, 1)


def test_build_item_ids_are_unique_across_calls():
    a = contracts.build_item("word_builder", "short_vowels", CAT, 1)
    b = contracts.build_item("word_builder", "short_vowels", CAT, 1)
    assert a["item_id"] != b["item_id"]


def test_build_item_uses_canned_why_for_known_skill():
    item = contracts.build_item("word_builder", "digraphs", SHIP, 1)
    assert item["why"]["rule_id"] == "digraph_one_sound"
    assert "sh" in item["why"]["text_fallback"] or "Two letters" in item["why"]["text_fallback"]


def test_build_item_default_why_for_unknown_skill():
    item = contracts.build_item("word_builder", "some_unmapped_skill", CAT, 1)
    assert item["why"]["rule_id"] == "sound_it_out"


# --------------------------------------------------------------- word_builder payload
def test_word_builder_sound_boxes_digraph_and_single_widths():
    item = contracts.build_item("word_builder", "digraphs", SHIP, 1)
    boxes = item["payload"]["sound_boxes"]
    # ship -> phonemes ["sh","i","p"]: first box digraph, rest single
    assert boxes[0]["width"] == "digraph"
    assert boxes[1]["width"] == "single"
    assert boxes[2]["width"] == "single"


def test_word_builder_sound_boxes_all_single_for_cvc():
    item = contracts.build_item("word_builder", "short_vowels", CAT, 1)
    boxes = item["payload"]["sound_boxes"]
    assert all(b["width"] == "single" for b in boxes)


def test_word_builder_tiles_include_phonemes():
    item = contracts.build_item("word_builder", "digraphs", SHIP, 1)
    tiles = item["payload"]["tiles"]
    for p in SHIP["phonemes"]:
        assert p in tiles


def test_word_builder_tiles_include_distractors_when_provided():
    item = contracts.build_item("word_builder", "short_vowels", CAT, 1)
    tiles = item["payload"]["tiles"]
    for d in CAT["distractors"]:
        assert d in tiles


def test_word_builder_falls_back_to_pool_distractors_when_entry_has_none():
    entry = copy.deepcopy(LOVE)
    entry["distractors"] = []  # explicitly empty -> falls back to pool
    item = contracts.build_item(
        "word_builder", "heart_words", entry, 1, distractor_pool=["x", "y", "z"]
    )
    tiles = item["payload"]["tiles"]
    assert "x" in tiles and "y" in tiles


# --------------------------------------------------------------- letter_boxes payload
def test_letter_boxes_phoneme_groups_ship():
    item = contracts.build_item("letter_boxes", "digraphs", SHIP, 1)
    assert item["payload"]["phoneme_groups"] == [[0, 1], [2], [3]]
    assert len(item["payload"]["boxes"]) == len("ship")


def test_letter_boxes_phoneme_groups_cat():
    item = contracts.build_item("letter_boxes", "short_vowels", CAT, 1)
    assert item["payload"]["phoneme_groups"] == [[0], [1], [2]]


# --------------------------------------------------------------- echo_dictation payload
def test_echo_dictation_payload_is_empty_dict():
    item = contracts.build_item("echo_dictation", "short_vowels", CAT, 1)
    assert item["payload"] == {}


def test_auto_speak_true_only_for_dictation_types():
    # ADR-014: all dictation types (word, phrase, sentence) auto-speak on show
    for ex_type in contracts.EXERCISE_TYPES:
        item = contracts.build_item(ex_type, "short_vowels", CAT, 1)
        expected = ex_type in ("echo_dictation", "phrase_dictation", "sentence_scribe")
        assert item["prompt"]["auto_speak"] is expected


# --------------------------------------------------------------- public_item
def test_public_item_removes_target():
    item = contracts.build_item("word_builder", "short_vowels", CAT, 1)
    safe = contracts.public_item(item)
    assert "target" not in safe


def test_public_item_why_reduced_to_markers_only():
    item = contracts.build_item("word_builder", "heart_words", LOVE, 1)
    safe = contracts.public_item(item)
    assert set(safe["why"].keys()) == {"markers"}
    assert safe["why"]["markers"] == item["why"]["markers"]
    assert "text_fallback" not in safe["why"]
    assert "rule_id" not in safe["why"]


def test_public_item_retains_other_envelope_keys():
    item = contracts.build_item("word_builder", "short_vowels", CAT, 1)
    safe = contracts.public_item(item)
    expected_keys = (contracts._ENVELOPE_KEYS - {"target"})
    assert expected_keys <= set(safe.keys())
    for k in ("contract_version", "item_id", "type", "skill_id", "prompt", "payload",
              "grading", "scaffold_level", "source"):
        assert safe[k] == item[k]


# --------------------------------------------------------------- validate_item
def test_validate_item_missing_required_key():
    item = contracts.build_item("word_builder", "short_vowels", CAT, 1)
    del item["grading"]
    assert contracts.validate_item(item) is False


def test_validate_item_wrong_contract_version():
    item = contracts.build_item("word_builder", "short_vowels", CAT, 1)
    item["contract_version"] = 2
    assert contracts.validate_item(item) is False


def test_validate_item_unknown_type():
    item = contracts.build_item("word_builder", "short_vowels", CAT, 1)
    item["type"] = "not_a_real_type"
    assert contracts.validate_item(item) is False


def test_validate_item_empty_target():
    item = contracts.build_item("word_builder", "short_vowels", CAT, 1)
    item["target"] = ""
    assert contracts.validate_item(item) is False


def test_validate_item_non_str_target():
    item = contracts.build_item("word_builder", "short_vowels", CAT, 1)
    item["target"] = 123
    assert contracts.validate_item(item) is False


def test_validate_item_non_dict_payload():
    item = contracts.build_item("word_builder", "short_vowels", CAT, 1)
    item["payload"] = "not a dict"
    assert contracts.validate_item(item) is False


def test_validate_item_word_builder_missing_tiles():
    item = contracts.build_item("word_builder", "short_vowels", CAT, 1)
    del item["payload"]["tiles"]
    assert contracts.validate_item(item) is False


def test_validate_item_letter_boxes_missing_phoneme_groups():
    item = contracts.build_item("letter_boxes", "short_vowels", CAT, 1)
    del item["payload"]["phoneme_groups"]
    assert contracts.validate_item(item) is False


def test_validate_item_not_a_dict():
    assert contracts.validate_item("not a dict") is False
    assert contracts.validate_item(None) is False
    assert contracts.validate_item([]) is False


def test_validate_item_echo_dictation_always_valid_dict_payload():
    item = contracts.build_item("echo_dictation", "short_vowels", CAT, 1)
    assert contracts.validate_item(item) is True


# --------------------------------------------------------------- phoneme_letter_groups
def test_phoneme_letter_groups_correct_grouping_ship():
    assert contracts.phoneme_letter_groups("ship", ["sh", "i", "p"]) == [[0, 1], [2], [3]]


def test_phoneme_letter_groups_correct_grouping_cat():
    assert contracts.phoneme_letter_groups("cat", ["c", "a", "t"]) == [[0], [1], [2]]


def test_phoneme_letter_groups_mismatch_degrades_gracefully_covers_all_letters():
    # phonemes that don't line up with the word's letters at all
    word = "love"
    phonemes = ["zz", "qq"]  # neither matches love[0:2] or subsequent slices
    groups = contracts.phoneme_letter_groups(word, phonemes)
    # every letter index must be covered exactly once, no crash
    covered = sorted(i for g in groups for i in g)
    assert covered == list(range(len(word)))


def test_phoneme_letter_groups_leftover_letters_get_own_box():
    # phonemes shorter than the word -> leftover letters each get their own box
    word = "chat"
    phonemes = ["ch"]  # only covers 2 of 4 letters
    groups = contracts.phoneme_letter_groups(word, phonemes)
    assert groups[0] == [0, 1]
    assert groups[1:] == [[2], [3]]
    covered = sorted(i for g in groups for i in g)
    assert covered == list(range(len(word)))


# --------------------------------------------------------------- _markers_for
def test_markers_for_heart_word_tricky_letters():
    markers = contracts._markers_for(LOVE)
    assert markers == [[1], [3]]


def test_markers_for_digraph_word_no_tricky():
    markers = contracts._markers_for(SHIP)
    # ship: sh spans [0,1] (multi-letter), i and p are single -> only the digraph span
    assert markers == [[0, 1]]


def test_markers_for_plain_cvc_no_tricky_no_digraph():
    markers = contracts._markers_for(CAT)
    assert markers == []


# --------------------------------------------------------------- tool_schemas
def test_tool_schemas_one_per_exercise_type():
    schemas = contracts.tool_schemas()
    assert len(schemas) == len(contracts.EXERCISE_TYPES)


def test_tool_schemas_names_and_required_fields():
    schemas = contracts.tool_schemas()
    names = {s["function"]["name"] for s in schemas}
    assert names == {f"emit_{t}" for t in contracts.EXERCISE_TYPES}
    for s in schemas:
        required = s["function"]["parameters"]["required"]
        assert "skill_id" in required
        assert "target" in required


def test_tool_schemas_word_builder_has_distractors_prop():
    schemas = contracts.tool_schemas()
    wb = next(s for s in schemas if s["function"]["name"] == "emit_word_builder")
    assert "distractors" in wb["function"]["parameters"]["properties"]


# --------------------------------------------------------------- json_schema
def test_json_schema_has_envelope_keys_under_properties():
    schema = contracts.json_schema()
    assert set(contracts._ENVELOPE_KEYS) <= set(schema["properties"].keys())
    assert schema["properties"]["contract_version"]["const"] == contracts.CONTRACT_VERSION
    assert schema["properties"]["type"]["enum"] == list(contracts.EXERCISE_TYPES)
