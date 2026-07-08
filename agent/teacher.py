"""The teacher-agent's call sites (ADR-012), each with a deterministic fallback.

Phase-1 hook: kid-voice correction feedback. The prompt builders accept ONLY
words, error tags, skill ids and rule ids — never the child's name/age/profile
(invariant #2). The child is "the student". Any failure, timeout, invalid output,
or the live flag being off ⇒ the caller's canned line is returned (ADR-002): the
app never stalls or degrades because of the agent.

Live calls are gated behind SPELLQUEST_AGENT_LIVE so tests and default dev runs
are deterministic and never spend — the owner opts in for real sessions.
"""
from __future__ import annotations

import os

from . import client


def is_available() -> bool:
    """Live agent enrichment is on only when a key exists AND the owner opted in."""
    return client.is_configured() and os.environ.get("SPELLQUEST_AGENT_LIVE") == "1"


def _feedback_prompt(target: str, primary_tag: str, rule_id: str) -> list[dict]:
    """PII-safe (invariant #2): only the word, the error type, and the rule id.
    No name/age/profile ever enters a prompt."""
    system = (
        "You are a warm, playful spelling coach for a 7-year-old with dyslexia. "
        "In ONE short, kind sentence a young child understands, explain how to "
        "spell the word correctly and why. Be encouraging, never scolding. Do not "
        "repeat any wrong spelling. Refer to the learner as 'the student' if needed."
    )
    user = (
        f"The correct word is '{target}'. The mistake type was '{primary_tag}' "
        f"(rule: {rule_id}). Give one friendly sentence about how to get it right."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _valid_feedback(text: str) -> bool:
    """Guard against junk/oversized model output before it reaches the child."""
    return bool(text) and len(text) <= 220


def feedback_for(
    target: str, primary_tag: str, rule_id: str, canned: str, *, timeout: float = 4.0
) -> str:
    """One kid-voice correction sentence. Returns `canned` on any failure or when
    the agent is unavailable (ADR-002 fallback). Never raises."""
    if not is_available():
        return canned
    try:
        resp = client.chat(_feedback_prompt(target, primary_tag, rule_id), timeout=timeout, max_tokens=80)
        text = (client.first_message(resp).get("content") or "").strip()
        return text if _valid_feedback(text) else canned
    except client.AgentError:
        return canned
