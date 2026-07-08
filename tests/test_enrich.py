"""Tests for agent/enrich.py — AI enrichment of word-bank entries (T-015,
ADR-012 "AI enriches, engine leads"). NOTHING here touches the network:
`enrich_batch` calls `client.chat`, which is monkeypatched on
`agent.enrich.client` to return canned response dicts. If a test here ever
hits the network, that's a test bug.
"""
from __future__ import annotations

import pytest

from agent import client, enrich


# --------------------------------------------------------------- build_messages
def test_build_messages_returns_system_and_user():
    messages = enrich.build_messages(["cat", "dog"])
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"


def test_build_messages_user_content_contains_both_words():
    messages = enrich.build_messages(["cat", "dog"])
    user_content = messages[1]["content"]
    assert "cat" in user_content
    assert "dog" in user_content


def test_build_messages_system_content_is_nonempty_instructions():
    messages = enrich.build_messages(["cat"])
    assert isinstance(messages[0]["content"], str)
    assert len(messages[0]["content"]) > 0


# --------------------------------------------------------------- parse_enrichment: happy path
def test_parse_enrichment_clean_json_array():
    content = (
        '[{"word":"Cat","phrase":"a cat","sentence":"The cat naps.","emoji":"\U0001F431"}]'
    )
    result = enrich.parse_enrichment(content)
    assert "cat" in result
    assert result["cat"]["phrase"] == "a cat"
    assert result["cat"]["sentence"] == "The cat naps."
    assert result["cat"]["emoji"] == "\U0001F431"


def test_parse_enrichment_lowercases_word_key():
    content = '[{"word":"DOG","phrase":"a dog","sentence":"The dog runs.","emoji":"🐶"}]'
    result = enrich.parse_enrichment(content)
    assert "dog" in result
    assert "DOG" not in result


def test_parse_enrichment_multiple_words():
    content = (
        '[{"word":"cat","phrase":"a cat","sentence":"The cat naps.","emoji":"🐱"},'
        '{"word":"dog","phrase":"a dog","sentence":"The dog runs.","emoji":"🐶"}]'
    )
    result = enrich.parse_enrichment(content)
    assert set(result.keys()) == {"cat", "dog"}


# --------------------------------------------------------------- parse_enrichment: tolerant extraction
def test_parse_enrichment_extracts_from_code_fence():
    content = (
        "```json\n"
        '[{"word":"cat","phrase":"a cat","sentence":"The cat naps.","emoji":"🐱"}]\n'
        "```"
    )
    result = enrich.parse_enrichment(content)
    assert "cat" in result
    assert result["cat"]["sentence"] == "The cat naps."


def test_parse_enrichment_extracts_with_surrounding_prose():
    content = (
        "Sure, here you go!\n"
        '[{"word":"cat","phrase":"a cat","sentence":"The cat naps.","emoji":"🐱"}]\n'
        "Hope that helps!"
    )
    result = enrich.parse_enrichment(content)
    assert "cat" in result


# --------------------------------------------------------------- parse_enrichment: empty / malformed
def test_parse_enrichment_empty_string_returns_empty_dict():
    assert enrich.parse_enrichment("") == {}


def test_parse_enrichment_none_returns_empty_dict():
    assert enrich.parse_enrichment(None) == {}


def test_parse_enrichment_no_array_returns_empty_dict():
    assert enrich.parse_enrichment("just some prose, no brackets here") == {}


def test_parse_enrichment_malformed_json_returns_empty_dict():
    # Has brackets so the regex matches, but the JSON inside is broken.
    assert enrich.parse_enrichment("[{word: 'cat', not valid json}]") == {}


def test_parse_enrichment_json_array_of_scalars_not_dicts_returns_empty():
    # Valid JSON array, but rows aren't dicts — every row should be skipped.
    assert enrich.parse_enrichment('["cat", "dog", 3]') == {}


# --------------------------------------------------------------- parse_enrichment: row-level tolerance
def test_parse_enrichment_skips_non_dict_rows_mixed_with_valid_rows():
    content = '["not-a-dict", {"word":"cat","phrase":"a cat","sentence":"The cat naps.","emoji":"🐱"}]'
    result = enrich.parse_enrichment(content)
    assert set(result.keys()) == {"cat"}


def test_parse_enrichment_skips_row_with_missing_word():
    content = '[{"phrase":"a cat","sentence":"The cat naps.","emoji":"🐱"}]'
    result = enrich.parse_enrichment(content)
    assert result == {}


def test_parse_enrichment_skips_row_with_empty_word():
    content = '[{"word":"","phrase":"a cat","sentence":"The cat naps.","emoji":"🐱"}]'
    result = enrich.parse_enrichment(content)
    assert result == {}


def test_parse_enrichment_skips_row_with_whitespace_only_word():
    content = '[{"word":"   ","phrase":"a cat","sentence":"The cat naps.","emoji":"🐱"}]'
    result = enrich.parse_enrichment(content)
    assert result == {}


def test_parse_enrichment_missing_phrase_sentence_emoji_default_to_empty_string():
    content = '[{"word":"cat"}]'
    result = enrich.parse_enrichment(content)
    assert result["cat"] == {"phrase": "", "sentence": "", "emoji": ""}


def test_parse_enrichment_null_phrase_sentence_emoji_default_to_empty_string():
    content = '[{"word":"cat","phrase":null,"sentence":null,"emoji":null}]'
    result = enrich.parse_enrichment(content)
    assert result["cat"] == {"phrase": "", "sentence": "", "emoji": ""}


# --------------------------------------------------------------- is_valid
def test_is_valid_true_for_good_enrichment():
    enrichment = {"phrase": "a cat", "sentence": "The cat naps.", "emoji": "🐱"}
    assert enrich.is_valid("cat", enrichment) is True


def test_is_valid_case_insensitive_word_match():
    enrichment = {"phrase": "a Cat", "sentence": "The CAT naps.", "emoji": "🐱"}
    assert enrich.is_valid("cat", enrichment) is True


def test_is_valid_true_when_emoji_empty():
    enrichment = {"phrase": "a cat", "sentence": "The cat naps.", "emoji": ""}
    assert enrich.is_valid("cat", enrichment) is True


def test_is_valid_false_when_sentence_missing():
    enrichment = {"phrase": "a cat", "emoji": "🐱"}
    assert enrich.is_valid("cat", enrichment) is False


def test_is_valid_false_when_sentence_empty():
    enrichment = {"phrase": "a cat", "sentence": "", "emoji": "🐱"}
    assert enrich.is_valid("cat", enrichment) is False


def test_is_valid_false_when_phrase_missing():
    enrichment = {"sentence": "The cat naps.", "emoji": "🐱"}
    assert enrich.is_valid("cat", enrichment) is False


def test_is_valid_false_when_phrase_empty():
    enrichment = {"phrase": "", "sentence": "The cat naps.", "emoji": "🐱"}
    assert enrich.is_valid("cat", enrichment) is False


def test_is_valid_false_when_word_not_in_sentence():
    enrichment = {"phrase": "a dog", "sentence": "The dog runs.", "emoji": "🐶"}
    assert enrich.is_valid("cat", enrichment) is False


def test_is_valid_false_when_sentence_too_long():
    long_sentence = "The cat " + ("naps and plays and runs " * 5) + "cat."
    assert len(long_sentence) > 80
    enrichment = {"phrase": "a cat", "sentence": long_sentence, "emoji": "🐱"}
    assert enrich.is_valid("cat", enrichment) is False


def test_is_valid_true_when_sentence_exactly_80_chars():
    # Boundary: len > 80 fails, so exactly 80 must pass.
    base = "The cat "
    filler = "x" * (80 - len(base))
    sentence = base + filler
    assert len(sentence) == 80
    enrichment = {"phrase": "a cat", "sentence": sentence, "emoji": "🐱"}
    assert enrich.is_valid("cat", enrichment) is True


def test_is_valid_false_when_phrase_too_long():
    long_phrase = "a very very very long phrase about a cat indeed"
    assert len(long_phrase) > 40
    enrichment = {"phrase": long_phrase, "sentence": "The cat naps.", "emoji": "🐱"}
    assert enrich.is_valid("cat", enrichment) is False


def test_is_valid_true_when_phrase_exactly_40_chars():
    phrase = "x" * 40
    assert len(phrase) == 40
    enrichment = {"phrase": phrase, "sentence": "The cat naps.", "emoji": "🐱"}
    assert enrich.is_valid("cat", enrichment) is True


# --------------------------------------------------------------- enrich_batch
def _fake_response(content: str) -> dict:
    return {"choices": [{"message": {"role": "assistant", "content": content}}]}


def test_enrich_batch_returns_only_valid_entries(monkeypatch):
    # "cat" is valid (sentence contains the word); "dog" is invalid (sentence
    # doesn't contain "dog" at all).
    content = (
        '[{"word":"cat","phrase":"a cat","sentence":"The cat naps.","emoji":"🐱"},'
        '{"word":"dog","phrase":"a dog","sentence":"It runs fast.","emoji":"🐶"}]'
    )

    def _fake_chat(messages, *, timeout=30.0, temperature=0.7, max_tokens=1200):
        return _fake_response(content)

    monkeypatch.setattr(enrich.client, "chat", _fake_chat)

    result = enrich.enrich_batch(["cat", "dog"])

    assert set(result.keys()) == {"cat"}
    assert result["cat"]["sentence"] == "The cat naps."


def test_enrich_batch_filters_words_not_in_requested_batch(monkeypatch):
    # Model returns an extra word ("bird") that wasn't requested — must be
    # filtered out even though it's individually valid.
    content = (
        '[{"word":"cat","phrase":"a cat","sentence":"The cat naps.","emoji":"🐱"},'
        '{"word":"bird","phrase":"a bird","sentence":"The bird flies.","emoji":"🐦"}]'
    )

    def _fake_chat(messages, *, timeout=30.0, temperature=0.7, max_tokens=1200):
        return _fake_response(content)

    monkeypatch.setattr(enrich.client, "chat", _fake_chat)

    result = enrich.enrich_batch(["cat"])

    assert set(result.keys()) == {"cat"}


def test_enrich_batch_word_matching_is_case_insensitive(monkeypatch):
    content = '[{"word":"Cat","phrase":"a cat","sentence":"The cat naps.","emoji":"🐱"}]'

    def _fake_chat(messages, *, timeout=30.0, temperature=0.7, max_tokens=1200):
        return _fake_response(content)

    monkeypatch.setattr(enrich.client, "chat", _fake_chat)

    result = enrich.enrich_batch(["CAT"])

    assert set(result.keys()) == {"cat"}


def test_enrich_batch_unparseable_content_returns_empty_dict(monkeypatch):
    def _fake_chat(messages, *, timeout=30.0, temperature=0.7, max_tokens=1200):
        return _fake_response("no json here at all")

    monkeypatch.setattr(enrich.client, "chat", _fake_chat)

    result = enrich.enrich_batch(["cat", "dog"])

    assert result == {}


def test_enrich_batch_all_invalid_returns_empty_dict(monkeypatch):
    content = (
        '[{"word":"cat","phrase":"a cat","sentence":"nope.","emoji":"🐱"},'
        '{"word":"dog","phrase":"a dog","sentence":"nope.","emoji":"🐶"}]'
    )

    def _fake_chat(messages, *, timeout=30.0, temperature=0.7, max_tokens=1200):
        return _fake_response(content)

    monkeypatch.setattr(enrich.client, "chat", _fake_chat)

    result = enrich.enrich_batch(["cat", "dog"])

    assert result == {}


def test_enrich_batch_propagates_agent_error(monkeypatch):
    def _raise_agent_error(messages, *, timeout=30.0, temperature=0.7, max_tokens=1200):
        raise client.AgentError("agent call failed: URLError")

    monkeypatch.setattr(enrich.client, "chat", _raise_agent_error)

    with pytest.raises(client.AgentError):
        enrich.enrich_batch(["cat", "dog"])


def test_enrich_batch_passes_words_to_build_messages(monkeypatch):
    captured = {}

    def _fake_chat(messages, *, timeout=30.0, temperature=0.7, max_tokens=1200):
        captured["messages"] = messages
        return _fake_response(
            '[{"word":"cat","phrase":"a cat","sentence":"The cat naps.","emoji":"🐱"}]'
        )

    monkeypatch.setattr(enrich.client, "chat", _fake_chat)

    enrich.enrich_batch(["cat"])

    assert "cat" in captured["messages"][1]["content"]
