"""Strict emoji audit for the word banks (owner mandate 2026-07-09).

The picture next to a word is a CUE for a dyslexic child: if it doesn't
unmistakably depict the word itself, it teaches the wrong word (she hears
"big", sees 🐕, types "dog"). Rule: an emoji is kept only when it clearly IS
the word; concrete nouns mostly qualify; actions/adjectives/function words
usually get NONE (the UI shows a neutral placeholder instead).

DeepSeek is the judge; output is validated hard — a bad verdict falls back to
REMOVE (no image beats a wrong image).
"""
from __future__ import annotations

import json
import re

from . import client

_SYSTEM = (
    "You audit picture cues for a spelling game for a 6-year-old with dyslexia. "
    "For each (word, emoji) pair decide STRICTLY: would this emoji make the child "
    "think of EXACTLY this word — not a related word? A picture that suggests a "
    "different word (a dog for 'big', a glass for 'sip', yarn for 'rug') is "
    "harmful: she may spell the pictured word instead. Verdicts: "
    "'keep' (the emoji unmistakably depicts this exact word), "
    "'replace' (a different emoji unmistakably depicts it — give it), "
    "'remove' (no emoji clearly depicts it — actions, adjectives, function words "
    "usually land here; when unsure, remove). "
    "Return ONLY a JSON array: [{\"word\":..,\"verdict\":\"keep|replace|remove\","
    "\"emoji\":\"<replacement or empty>\"}]. No prose."
)


def build_messages(rows: list[dict]) -> list[dict]:
    """rows: [{word, emoji, phrase}] — the phrase gives usage context only."""
    lines = [f"{r['word']} | current: {r.get('emoji') or '(none)'} | used as: {r.get('phrase') or ''}" for r in rows]
    return [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": "Audit these:\n" + "\n".join(lines)},
    ]


def _valid_emoji(text: str) -> bool:
    """A plausible emoji: short, no letters/digits/whitespace."""
    t = (text or "").strip()
    return 0 < len(t) <= 8 and not re.search(r"[A-Za-z0-9\s]", t)


def parse_verdicts(content: str, requested: set[str]) -> dict[str, str]:
    """{word: final_emoji} for every VALID verdict ('' means remove). Malformed
    rows and unknown words are dropped; an invalid 'replace' emoji degrades to
    remove (never keep a dubious image)."""
    match = re.search(r"\[.*\]", content or "", re.DOTALL)
    if not match:
        return {}
    try:
        rows = json.loads(match.group(0))
    except (ValueError, TypeError):
        return {}
    out: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        word = str(row.get("word", "")).strip().lower()
        verdict = str(row.get("verdict", "")).strip().lower()
        emoji = str(row.get("emoji", "") or "").strip()
        if word not in requested:
            continue
        if verdict == "keep":
            continue  # unchanged — not in the output map
        if verdict == "replace" and _valid_emoji(emoji):
            out[word] = emoji
        elif verdict in ("replace", "remove"):
            out[word] = ""  # dubious replacement or explicit removal → no image
    return out


def review_batch(rows: list[dict], *, timeout: float = 40.0) -> dict[str, str]:
    """One judge call. Returns {word: new_emoji_or_empty} for words that CHANGE.
    Raises client.AgentError on transport failure."""
    resp = client.chat(build_messages(rows), timeout=timeout, temperature=0.1, max_tokens=1500)
    return parse_verdicts(client.first_message(resp).get("content", ""), {r["word"] for r in rows})


# ------------------------------------------------------------- back-translation
_REVERSE_SYSTEM = (
    "You will see emojis, one per line, numbered. For EACH, answer: what single "
    "English word would a 6-year-old child most likely say when seeing ONLY this "
    "emoji? Return ONLY a JSON array: [{\"n\":<number>,\"word\":\"...\"}]. No prose."
)


def build_reverse_messages(emojis: list[str]) -> list[dict]:
    lines = [f"{i + 1}. {e}" for i, e in enumerate(emojis)]
    return [
        {"role": "system", "content": _REVERSE_SYSTEM},
        {"role": "user", "content": "\n".join(lines)},
    ]


def parse_reverse(content: str, count: int) -> dict[int, str]:
    """{index(0-based): word} from the reverse pass; malformed rows dropped."""
    match = re.search(r"\[.*\]", content or "", re.DOTALL)
    if not match:
        return {}
    try:
        rows = json.loads(match.group(0))
    except (ValueError, TypeError):
        return {}
    out: dict[int, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            n = int(row.get("n"))
        except (TypeError, ValueError):
            continue
        if 1 <= n <= count:
            out[n - 1] = str(row.get("word", "")).strip().lower()
    return out


def words_match(word: str, said: str) -> bool:
    """The back-translation test: does the child's word for the emoji equal OUR
    word? Exact match with simple plural tolerance — anything else fails (a
    'related' picture is exactly the harmful kind)."""
    w, s = word.strip().lower(), said.strip().lower()
    return bool(s) and (s == w or s == w + "s" or w == s + "s")


def verify_batch(pairs: list[tuple[str, str]], *, timeout: float = 40.0) -> set[str]:
    """Back-translate emojis alone and return the WORDS whose image FAILED the
    test (child would say a different word) → callers remove those images. A
    word with no parseable reverse answer fails too (never keep a dubious cue).
    Raises client.AgentError on transport failure."""
    emojis = [e for _, e in pairs]
    resp = client.chat(build_reverse_messages(emojis), timeout=timeout, temperature=0.0, max_tokens=1200)
    said = parse_reverse(client.first_message(resp).get("content", ""), len(pairs))
    failed: set[str] = set()
    for i, (word, _emoji) in enumerate(pairs):
        if not words_match(word, said.get(i, "")):
            failed.add(word)
    return failed
