"""Tests for agent/teacher.py — the teacher call sites (ADR-012), the
always-fallback rule (ADR-002), and the PII boundary (invariant #2).

`agent.client.chat` is monkeypatched wherever a "live" call is exercised, so
these tests never touch the network. `is_available()` gating means most
`feedback_for` tests don't even reach `client.chat` unless both env vars are
set.
"""
from __future__ import annotations

import pytest

from agent import client, teacher


CANNED = "Let's say the sounds slowly and write each one."


# --------------------------------------------------------------- is_available
def test_is_available_true_when_key_and_flag_set(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key")
    monkeypatch.setenv("SPELLQUEST_AGENT_LIVE", "1")
    assert teacher.is_available() is True


def test_is_available_false_when_no_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("SPELLQUEST_AGENT_LIVE", "1")
    assert teacher.is_available() is False


def test_is_available_false_when_flag_unset(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key")
    monkeypatch.delenv("SPELLQUEST_AGENT_LIVE", raising=False)
    assert teacher.is_available() is False


@pytest.mark.parametrize("flag_value", ["0", "true", "yes", "TRUE", "", "on"])
def test_is_available_false_for_non_1_flag_values(monkeypatch, flag_value):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key")
    monkeypatch.setenv("SPELLQUEST_AGENT_LIVE", flag_value)
    assert teacher.is_available() is False


def test_is_available_false_when_neither_set(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("SPELLQUEST_AGENT_LIVE", raising=False)
    assert teacher.is_available() is False


# --------------------------------------------------------------- feedback_for: agent off
def test_feedback_for_returns_canned_when_agent_off_no_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("SPELLQUEST_AGENT_LIVE", raising=False)
    result = teacher.feedback_for("love", "phonetic_plausible", "magic_e_v_bodyguard", CANNED)
    assert result == CANNED


def test_feedback_for_returns_canned_when_agent_off_flag_unset(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key")
    monkeypatch.delenv("SPELLQUEST_AGENT_LIVE", raising=False)
    result = teacher.feedback_for("love", "phonetic_plausible", "magic_e_v_bodyguard", CANNED)
    assert result == CANNED


def test_feedback_for_agent_off_never_calls_chat(monkeypatch):
    """When unavailable, feedback_for must not even attempt a client.chat call."""
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("SPELLQUEST_AGENT_LIVE", raising=False)

    def _boom(*args, **kwargs):
        raise AssertionError("client.chat should not be called when agent is unavailable")

    monkeypatch.setattr(client, "chat", _boom)
    result = teacher.feedback_for("love", "phonetic_plausible", "magic_e_v_bodyguard", CANNED)
    assert result == CANNED


# --------------------------------------------------------------- feedback_for: agent on, success
def test_feedback_for_returns_model_sentence_when_available(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key")
    monkeypatch.setenv("SPELLQUEST_AGENT_LIVE", "1")

    good_sentence = "Remember the silent e makes the o say its name, like a little bodyguard!"

    def _fake_chat(messages, *, timeout=None, max_tokens=None, **kwargs):
        return {"choices": [{"message": {"role": "assistant", "content": good_sentence}}]}

    monkeypatch.setattr(client, "chat", _fake_chat)

    result = teacher.feedback_for("love", "phonetic_plausible", "magic_e_v_bodyguard", CANNED)
    assert result == good_sentence


# --------------------------------------------------------------- feedback_for: failure modes
def test_feedback_for_returns_canned_on_agent_error(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key")
    monkeypatch.setenv("SPELLQUEST_AGENT_LIVE", "1")

    def _fake_chat(*args, **kwargs):
        raise client.AgentError("agent call failed: URLError")

    monkeypatch.setattr(client, "chat", _fake_chat)

    result = teacher.feedback_for("love", "phonetic_plausible", "magic_e_v_bodyguard", CANNED)
    assert result == CANNED


def test_feedback_for_returns_canned_on_empty_string_output(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key")
    monkeypatch.setenv("SPELLQUEST_AGENT_LIVE", "1")

    def _fake_chat(*args, **kwargs):
        return {"choices": [{"message": {"role": "assistant", "content": ""}}]}

    monkeypatch.setattr(client, "chat", _fake_chat)

    result = teacher.feedback_for("love", "phonetic_plausible", "magic_e_v_bodyguard", CANNED)
    assert result == CANNED


def test_feedback_for_returns_canned_on_whitespace_only_output(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key")
    monkeypatch.setenv("SPELLQUEST_AGENT_LIVE", "1")

    def _fake_chat(*args, **kwargs):
        return {"choices": [{"message": {"role": "assistant", "content": "   \n  "}}]}

    monkeypatch.setattr(client, "chat", _fake_chat)

    result = teacher.feedback_for("love", "phonetic_plausible", "magic_e_v_bodyguard", CANNED)
    assert result == CANNED


def test_feedback_for_returns_canned_on_too_long_output(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key")
    monkeypatch.setenv("SPELLQUEST_AGENT_LIVE", "1")

    too_long = "x" * 221  # > 220 chars

    def _fake_chat(*args, **kwargs):
        return {"choices": [{"message": {"role": "assistant", "content": too_long}}]}

    monkeypatch.setattr(client, "chat", _fake_chat)

    result = teacher.feedback_for("love", "phonetic_plausible", "magic_e_v_bodyguard", CANNED)
    assert result == CANNED


def test_feedback_for_accepts_output_at_exactly_220_chars(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key")
    monkeypatch.setenv("SPELLQUEST_AGENT_LIVE", "1")

    exactly_220 = "y" * 220

    def _fake_chat(*args, **kwargs):
        return {"choices": [{"message": {"role": "assistant", "content": exactly_220}}]}

    monkeypatch.setattr(client, "chat", _fake_chat)

    result = teacher.feedback_for("love", "phonetic_plausible", "magic_e_v_bodyguard", CANNED)
    assert result == exactly_220


def test_feedback_for_returns_canned_on_malformed_response_shape(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key")
    monkeypatch.setenv("SPELLQUEST_AGENT_LIVE", "1")

    def _fake_chat(*args, **kwargs):
        return {"unexpected": "shape"}  # no "choices" key at all

    monkeypatch.setattr(client, "chat", _fake_chat)

    result = teacher.feedback_for("love", "phonetic_plausible", "magic_e_v_bodyguard", CANNED)
    assert result == CANNED


# --------------------------------------------------------------- PII boundary (invariant #2)
def test_feedback_prompt_contains_only_target_tag_and_rule_no_pii():
    messages = teacher._feedback_prompt("love", "phonetic_plausible", "magic_e_v_bodyguard")

    assert isinstance(messages, list)
    assert len(messages) == 2
    system_msg, user_msg = messages
    assert system_msg["role"] == "system"
    assert user_msg["role"] == "user"

    # the target word, the tag, and the rule id must all appear in the user msg
    assert "love" in user_msg["content"]
    assert "phonetic_plausible" in user_msg["content"]
    assert "magic_e_v_bodyguard" in user_msg["content"]

    # no name-like PII: neither the system nor user message may reference a
    # child's name, age, or profile field. There is no name/profile parameter
    # to the function at all -- assert the whole prompt text is built only from
    # the three inputs plus fixed template copy (no stray identifiers).
    full_text = system_msg["content"] + " " + user_msg["content"]
    banned_terms = ["name", "age", "profile", "display_name", "avatar", "daughter"]
    lowered = full_text.lower()
    for term in banned_terms:
        assert term not in lowered, f"unexpected PII-adjacent term {term!r} in prompt"

    # the child is referred to generically
    assert "student" in full_text.lower()


def test_feedback_prompt_does_not_leak_common_test_pii_markers():
    """Guardrail-style: if a caller somehow tried to smuggle identity data
    through target/tag/rule, this at least proves the function itself adds no
    additional PII fields -- the prompt is built purely from its 3 args."""
    messages = teacher._feedback_prompt("cat", "reversal", "sound_it_out")
    full_text = " ".join(m["content"] for m in messages)
    for pii_marker in ["7-year-old named", "Age:", "Daughter", "Emma", "Sophia"]:
        assert pii_marker not in full_text


def test_feedback_prompt_varies_only_by_its_three_inputs():
    """Same target/tag/rule ⇒ identical prompt every call (no hidden state /
    randomness / injected profile data)."""
    m1 = teacher._feedback_prompt("cat", "reversal", "sound_it_out")
    m2 = teacher._feedback_prompt("cat", "reversal", "sound_it_out")
    assert m1 == m2
