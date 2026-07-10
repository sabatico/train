"""Tests for agent/emoji_review.py — strict emoji audit + back-translation
verification (owner mandate 2026-07-09). NOTHING here touches the network:
`review_batch` / `verify_batch` call `client.chat`, which is monkeypatched on
`agent.emoji_review.client` to return canned response dicts. If a test here
ever hits the network, that's a test bug.
"""
from __future__ import annotations

import pytest

from agent import client, emoji_review


def _fake_response(content: str) -> dict:
    return {"choices": [{"message": {"role": "assistant", "content": content}}]}


# --------------------------------------------------------------- _valid_emoji
def test_valid_emoji_simple_emoji_true():
    assert emoji_review._valid_emoji("🐶") is True


def test_valid_emoji_multi_codepoint_within_length_true():
    # ZWJ sequence "🧑‍🤝‍🧑" (people holding hands) — multiple codepoints, no
    # letters/digits/whitespace, len <= 8.
    assert len("🧑‍🤝‍🧑") <= 8
    assert emoji_review._valid_emoji("🧑‍🤝‍🧑") is True


def test_valid_emoji_empty_string_false():
    assert emoji_review._valid_emoji("") is False


def test_valid_emoji_letters_false():
    assert emoji_review._valid_emoji("abc") is False


def test_valid_emoji_mixed_letter_and_emoji_false():
    assert emoji_review._valid_emoji("a🐶") is False


def test_valid_emoji_with_space_false():
    assert emoji_review._valid_emoji("🐶 🐱") is False


def test_valid_emoji_too_long_false():
    # 9+ chars (after strip) is rejected even if all valid emoji-ish chars.
    text = "🐶" * 9
    assert len(text) > 8
    assert emoji_review._valid_emoji(text) is False


def test_valid_emoji_none_input_false():
    assert emoji_review._valid_emoji(None) is False


def test_valid_emoji_whitespace_only_false():
    assert emoji_review._valid_emoji("   ") is False


# --------------------------------------------------------------- parse_verdicts: keep
def test_parse_verdicts_keep_word_absent_from_result():
    content = '[{"word":"cat","verdict":"keep","emoji":"🐱"}]'
    result = emoji_review.parse_verdicts(content, {"cat"})
    assert "cat" not in result
    assert result == {}


# --------------------------------------------------------------- parse_verdicts: replace
def test_parse_verdicts_replace_with_valid_emoji():
    content = '[{"word":"cat","verdict":"replace","emoji":"🐈"}]'
    result = emoji_review.parse_verdicts(content, {"cat"})
    assert result == {"cat": "🐈"}


def test_parse_verdicts_replace_with_invalid_emoji_degrades_to_remove():
    content = '[{"word":"cat","verdict":"replace","emoji":"kitty"}]'
    result = emoji_review.parse_verdicts(content, {"cat"})
    assert result == {"cat": ""}


# --------------------------------------------------------------- parse_verdicts: remove
def test_parse_verdicts_remove():
    content = '[{"word":"big","verdict":"remove","emoji":""}]'
    result = emoji_review.parse_verdicts(content, {"big"})
    assert result == {"big": ""}


# --------------------------------------------------------------- parse_verdicts: filtering
def test_parse_verdicts_unknown_word_dropped():
    content = '[{"word":"dog","verdict":"remove","emoji":""}]'
    result = emoji_review.parse_verdicts(content, {"cat"})
    assert result == {}


def test_parse_verdicts_non_dict_rows_dropped():
    content = '["not-a-dict", {"word":"cat","verdict":"remove","emoji":""}]'
    result = emoji_review.parse_verdicts(content, {"cat"})
    assert result == {"cat": ""}


def test_parse_verdicts_word_key_lowercased_matches_requested():
    content = '[{"word":"Cat","verdict":"remove","emoji":""}]'
    result = emoji_review.parse_verdicts(content, {"cat"})
    assert result == {"cat": ""}


# --------------------------------------------------------------- parse_verdicts: tolerant extraction
def test_parse_verdicts_extracts_from_code_fence():
    content = '```json\n[{"word":"cat","verdict":"remove","emoji":""}]\n```'
    result = emoji_review.parse_verdicts(content, {"cat"})
    assert result == {"cat": ""}


def test_parse_verdicts_extracts_with_surrounding_prose():
    content = 'Sure, here you go!\n[{"word":"cat","verdict":"remove","emoji":""}]\nHope that helps!'
    result = emoji_review.parse_verdicts(content, {"cat"})
    assert result == {"cat": ""}


# --------------------------------------------------------------- parse_verdicts: garbage
def test_parse_verdicts_garbage_returns_empty_dict():
    result = emoji_review.parse_verdicts("no json here at all", {"cat"})
    assert result == {}


def test_parse_verdicts_none_content_returns_empty_dict():
    result = emoji_review.parse_verdicts(None, {"cat"})
    assert result == {}


def test_parse_verdicts_no_array_returns_empty_dict():
    result = emoji_review.parse_verdicts("just prose, no brackets", {"cat"})
    assert result == {}


def test_parse_verdicts_malformed_json_returns_empty_dict():
    result = emoji_review.parse_verdicts("[{word: 'cat', not valid json}]", {"cat"})
    assert result == {}


def test_parse_verdicts_json_array_of_scalars_returns_empty():
    result = emoji_review.parse_verdicts('["cat", "dog", 3]', {"cat", "dog"})
    assert result == {}


def test_parse_verdicts_multiple_rows_mixed_verdicts():
    content = (
        '[{"word":"cat","verdict":"keep","emoji":"🐱"},'
        '{"word":"dog","verdict":"replace","emoji":"🐕"},'
        '{"word":"big","verdict":"remove","emoji":""},'
        '{"word":"unknown","verdict":"remove","emoji":""}]'
    )
    result = emoji_review.parse_verdicts(content, {"cat", "dog", "big"})
    assert result == {"dog": "🐕", "big": ""}
    assert "cat" not in result


# --------------------------------------------------------------- build_messages
def test_build_messages_returns_two_messages():
    rows = [{"word": "cat", "emoji": "🐱", "phrase": "a cat"}]
    messages = emoji_review.build_messages(rows)
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"


def test_build_messages_includes_word_emoji_and_phrase():
    rows = [{"word": "cat", "emoji": "🐱", "phrase": "a cat"}]
    content = emoji_review.build_messages(rows)[1]["content"]
    assert "cat" in content
    assert "🐱" in content
    assert "a cat" in content


def test_build_messages_multiple_rows_all_present():
    rows = [
        {"word": "cat", "emoji": "🐱", "phrase": "a cat"},
        {"word": "big", "emoji": "", "phrase": "a big dog"},
    ]
    content = emoji_review.build_messages(rows)[1]["content"]
    assert "cat" in content
    assert "big" in content
    assert "a big dog" in content


def test_build_messages_handles_missing_emoji_and_phrase():
    rows = [{"word": "cat"}]
    content = emoji_review.build_messages(rows)[1]["content"]
    assert "cat" in content
    assert "(none)" in content


# --------------------------------------------------------------- review_batch
def test_review_batch_returns_only_changed_words(monkeypatch):
    content = (
        '[{"word":"cat","verdict":"keep","emoji":"🐱"},'
        '{"word":"dog","verdict":"replace","emoji":"🐕"}]'
    )

    def _fake_chat(messages, *, timeout=40.0, temperature=0.1, max_tokens=1500):
        return _fake_response(content)

    monkeypatch.setattr(emoji_review.client, "chat", _fake_chat)

    rows = [
        {"word": "cat", "emoji": "🐱", "phrase": "a cat"},
        {"word": "dog", "emoji": "🐩", "phrase": "a dog"},
    ]
    result = emoji_review.review_batch(rows)

    assert result == {"dog": "🐕"}


def test_review_batch_filters_to_requested_batch(monkeypatch):
    # Model returns a verdict for a word not in this batch — must be dropped.
    content = (
        '[{"word":"cat","verdict":"remove","emoji":""},'
        '{"word":"bird","verdict":"remove","emoji":""}]'
    )

    def _fake_chat(messages, *, timeout=40.0, temperature=0.1, max_tokens=1500):
        return _fake_response(content)

    monkeypatch.setattr(emoji_review.client, "chat", _fake_chat)

    rows = [{"word": "cat", "emoji": "🐱", "phrase": "a cat"}]
    result = emoji_review.review_batch(rows)

    assert result == {"cat": ""}


def test_review_batch_propagates_agent_error(monkeypatch):
    def _raise_agent_error(messages, *, timeout=40.0, temperature=0.1, max_tokens=1500):
        raise client.AgentError("agent call failed: URLError")

    monkeypatch.setattr(emoji_review.client, "chat", _raise_agent_error)

    rows = [{"word": "cat", "emoji": "🐱", "phrase": "a cat"}]
    with pytest.raises(client.AgentError):
        emoji_review.review_batch(rows)


# --------------------------------------------------------------- build_reverse_messages
def test_build_reverse_messages_numbered_one_per_emoji():
    emojis = ["🐶", "📏", "🐱"]
    messages = emoji_review.build_reverse_messages(emojis)
    assert len(messages) == 2
    content = messages[1]["content"]
    assert "1. 🐶" in content
    assert "2. 📏" in content
    assert "3. 🐱" in content


def test_build_reverse_messages_system_role_first():
    messages = emoji_review.build_reverse_messages(["🐶"])
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"


# --------------------------------------------------------------- parse_reverse
def test_parse_reverse_basic_mapping():
    content = '[{"n":1,"word":"Dog"}]'
    result = emoji_review.parse_reverse(content, 1)
    assert result == {0: "dog"}


def test_parse_reverse_out_of_range_n_dropped():
    content = '[{"n":5,"word":"dog"}]'
    result = emoji_review.parse_reverse(content, 1)
    assert result == {}


def test_parse_reverse_n_zero_dropped():
    content = '[{"n":0,"word":"dog"}]'
    result = emoji_review.parse_reverse(content, 3)
    assert result == {}


def test_parse_reverse_non_int_n_dropped():
    content = '[{"n":"not-a-number","word":"dog"}]'
    result = emoji_review.parse_reverse(content, 1)
    assert result == {}


def test_parse_reverse_missing_n_dropped():
    content = '[{"word":"dog"}]'
    result = emoji_review.parse_reverse(content, 1)
    assert result == {}


def test_parse_reverse_malformed_json_returns_empty_dict():
    content = "[{n: 1, not valid json}]"
    result = emoji_review.parse_reverse(content, 1)
    assert result == {}


def test_parse_reverse_no_array_returns_empty_dict():
    result = emoji_review.parse_reverse("just prose", 1)
    assert result == {}


def test_parse_reverse_none_content_returns_empty_dict():
    result = emoji_review.parse_reverse(None, 1)
    assert result == {}


def test_parse_reverse_multiple_rows():
    content = '[{"n":1,"word":"dog"},{"n":2,"word":"ruler"}]'
    result = emoji_review.parse_reverse(content, 2)
    assert result == {0: "dog", 1: "ruler"}


def test_parse_reverse_non_dict_row_dropped():
    content = '["not-a-dict", {"n":1,"word":"dog"}]'
    result = emoji_review.parse_reverse(content, 1)
    assert result == {0: "dog"}


# --------------------------------------------------------------- words_match
def test_words_match_exact():
    assert emoji_review.words_match("dog", "dog") is True


def test_words_match_case_insensitive():
    assert emoji_review.words_match("dog", "Dogs") is True


def test_words_match_plural_tolerance_our_word_singular():
    assert emoji_review.words_match("cats", "cat") is True


def test_words_match_unrelated_words_false():
    assert emoji_review.words_match("big", "ruler") is False


def test_words_match_empty_said_false():
    assert emoji_review.words_match("sip", "") is False


def test_words_match_different_word_false():
    assert emoji_review.words_match("ship", "boat") is False


# --------------------------------------------------------------- verify_batch
def test_verify_batch_returns_failed_words(monkeypatch):
    # dog -> "dog" matches (pass); big/📏 -> "ruler" does not match "big" (fail).
    content = '[{"n":1,"word":"dog"},{"n":2,"word":"ruler"}]'

    def _fake_chat(messages, *, timeout=40.0, temperature=0.0, max_tokens=1200):
        return _fake_response(content)

    monkeypatch.setattr(emoji_review.client, "chat", _fake_chat)

    pairs = [("dog", "🐶"), ("big", "📏")]
    result = emoji_review.verify_batch(pairs)

    assert result == {"big"}


def test_verify_batch_missing_reverse_answer_fails(monkeypatch):
    # Only one of two pairs gets a reverse answer; the missing one must fail too.
    content = '[{"n":1,"word":"dog"}]'

    def _fake_chat(messages, *, timeout=40.0, temperature=0.0, max_tokens=1200):
        return _fake_response(content)

    monkeypatch.setattr(emoji_review.client, "chat", _fake_chat)

    pairs = [("dog", "🐶"), ("big", "📏")]
    result = emoji_review.verify_batch(pairs)

    assert result == {"big"}


def test_verify_batch_all_pass_returns_empty_set(monkeypatch):
    content = '[{"n":1,"word":"dog"},{"n":2,"word":"cat"}]'

    def _fake_chat(messages, *, timeout=40.0, temperature=0.0, max_tokens=1200):
        return _fake_response(content)

    monkeypatch.setattr(emoji_review.client, "chat", _fake_chat)

    pairs = [("dog", "🐶"), ("cat", "🐱")]
    result = emoji_review.verify_batch(pairs)

    assert result == set()


def test_verify_batch_propagates_agent_error(monkeypatch):
    def _raise_agent_error(messages, *, timeout=40.0, temperature=0.0, max_tokens=1200):
        raise client.AgentError("agent call failed: URLError")

    monkeypatch.setattr(emoji_review.client, "chat", _raise_agent_error)

    pairs = [("dog", "🐶")]
    with pytest.raises(client.AgentError):
        emoji_review.verify_batch(pairs)
