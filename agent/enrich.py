"""AI enrichment of word-bank entries (T-015, ADR-012 "AI enriches, engine leads").

DeepSeek generates the kid-friendly `phrase`, `sentence`, and `emoji` the
deterministic pipeline can't author. No child PII is involved (words only). Output
is VALIDATED before use — a word is only updated if the model returned a usable,
on-topic result; anything malformed is left untouched (the engine still works
without enrichment). This module is pure logic + the client call; the batch runner
is `scripts/enrich_wordbanks.py`.
"""
from __future__ import annotations

import json
import re

from . import client

_SYSTEM = (
    "You write playful, very simple content for a spelling game for a 7-year-old "
    "with dyslexia. For each word you are given, return: a 2-4 word 'phrase' that "
    "uses the word; a 'sentence' that is short (max 6 words), concrete, and uses "
    "the word; and one 'emoji' that best pictures the word (a single emoji, or '' "
    "if none fits). Keep it cheerful and age-appropriate. Return ONLY a JSON array "
    "of objects, each with keys: word, phrase, sentence, emoji. No prose."
)


def build_messages(words: list[str]) -> list[dict]:
    return [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": "Words: " + ", ".join(words)},
    ]


def parse_enrichment(content: str) -> dict[str, dict]:
    """Extract a {word: {phrase, sentence, emoji}} map from a model reply. Tolerant
    of code fences / surrounding text — pulls the first JSON array it finds."""
    if not content:
        return {}
    match = re.search(r"\[.*\]", content, re.DOTALL)
    if not match:
        return {}
    try:
        rows = json.loads(match.group(0))
    except (ValueError, TypeError):
        return {}
    out: dict[str, dict] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        word = str(row.get("word", "")).strip().lower()
        if word:
            out[word] = {
                "phrase": (row.get("phrase") or "").strip(),
                "sentence": (row.get("sentence") or "").strip(),
                "emoji": (row.get("emoji") or "").strip(),
            }
    return out


def is_valid(word: str, enrichment: dict) -> bool:
    """Accept an enrichment only if it's on-topic and sane: the sentence actually
    contains the word and is short-ish; phrase present. Emoji is optional."""
    sentence = enrichment.get("sentence", "")
    phrase = enrichment.get("phrase", "")
    if not sentence or not phrase:
        return False
    if word.lower() not in sentence.lower():
        return False
    if len(sentence) > 80 or len(phrase) > 40:
        return False
    return True


def enrich_batch(words: list[str], *, timeout: float = 30.0) -> dict[str, dict]:
    """One live call enriching a batch of words. Returns only the VALID results
    (keyed by word). Raises client.AgentError on transport failure (caller decides
    whether to retry/skip); returns {} on unparseable output."""
    resp = client.chat(build_messages(words), timeout=timeout, temperature=0.7, max_tokens=1200)
    parsed = parse_enrichment(client.first_message(resp).get("content", ""))
    return {w: e for w, e in parsed.items() if w in {x.lower() for x in words} and is_valid(w, e)}
