"""The exercise/interaction contract — one shape, three consumers (ADR-005).

This module is the SINGLE SOURCE of the item envelope + per-type payloads. The
Flask API sends these, the frontend registry renders them, and the DeepSeek agent
emits them (its tool schemas are generated here — ADR-012). Everything validates
against `validate_item` before use; invalid agent output falls back to the
deterministic item (ADR-002 rule 2).

Implementation note (within ADR-005's intent): the contract lives as Python specs
here rather than a hand-written .json + a jsonschema dependency — this keeps ONE
source that emits BOTH the validator and the agent tool-schemas, dependency-free
(CONVENTIONS: every dep is paid for). `json_schema()` renders the reference
`exercise.schema.json` artifact.
"""
from __future__ import annotations

import random
import re
import uuid

from . import config

CONTRACT_VERSION = 1

# The exercise types this contract knows (PLAN §3 / ADR-014). beat_yesterday is
# the remaining opt-in game (backlog T-013).
EXERCISE_TYPES = (
    "word_builder",
    "letter_boxes",
    "missing_letters",
    "word_sort",
    "heart_word_spotlight",
    "echo_dictation",
    "phrase_dictation",
    "sentence_scribe",
    "bd_ninja",
)
# Types whose target is a multi-word text (graded word-by-word, forgiving).
TEXT_TYPES = ("phrase_dictation", "sentence_scribe")

def _sound_out(phonemes: list[str]) -> str:
    """Format a word's sounds like '/p/ /u/ /p/'."""
    return " ".join(f"/{p}/" for p in phonemes)


def why_for(skill_id: str, word_entry: dict) -> tuple[str, str]:
    """The kid-voice explanation for THIS word — generated from its sounds, not a
    static template (PLAN §1: segment each sound, then blend to the word). Decodable
    patterns get the sound-by-sound blend; irregular heart words are learned whole.
    The agent may still replace the text at feedback time (ADR-012); this is the
    always-available, word-correct fallback (ADR-002)."""
    word = word_entry["word"]
    phonemes = word_entry.get("phonemes") or list(word)
    sounds = _sound_out(phonemes)
    if skill_id == "heart_words":
        return ("heart_word_by_heart", f"“{word}” is a heart word — learn it by heart ❤️.")
    if skill_id == "magic_e":
        return ("magic_e_silent", f"Magic e is silent — it makes the vowel say its name → {word}.")
    if skill_id == "digraphs":
        return ("digraph_one_sound", f"Two letters make one sound: {sounds} → {word}.")
    if skill_id == "vowel_teams":
        return ("vowel_team_one_sound", f"The vowel team makes one sound: {sounds} → {word}.")
    if skill_id == "r_controlled":
        return ("r_controlled", f"The r changes the vowel: {sounds} → {word}.")
    if skill_id in ("blends", "doubling_endings", "suffixes"):
        return ("blend_sounds", f"Blend each sound: {sounds} → {word}.")
    if skill_id == "letter_orientation":
        return ("bd_mirror", "b has its belly in FRONT — like a bat before the ball ⚾.")
    if skill_id == "phrase_dictation":
        return ("phrase_word_by_word", f"Say it slowly, one word at a time: {word}.")
    if skill_id == "sentence_writing":
        return ("sentence_word_by_word", f"Say it slowly and write word by word: {word}")
    # short_vowels + anything else: sound out each letter and blend
    return ("sound_it_out", f"Sound out each letter: {sounds} → {word}.")


# --------------------------------------------------------------- phoneme helpers
def phoneme_letter_groups(word: str, phonemes: list[str]) -> list[list[int]]:
    """Map each phoneme to the LETTER indices it spans (ship → [[0,1],[2],[3]]).

    Assumes the phonemes are the graphemes of the word in order (our word-bank
    encoding). Falls back to one-letter-per-index if they don't line up."""
    groups: list[list[int]] = []
    i = 0
    for p in phonemes:
        span = len(p)
        if word[i : i + span].lower() == p.lower():
            groups.append(list(range(i, i + span)))
            i += span
        else:  # encoding mismatch — degrade gracefully to single letters
            groups.append([i])
            i += 1
    if i != len(word):  # leftover letters → one box each
        groups.extend([[j] for j in range(i, len(word))])
    return groups


def _markers_for(word_entry: dict) -> list[list[int]]:
    """Index ranges the correction reveal highlights (ADR-005 `why.markers`):
    heart-word tricky letters, else the multi-letter (digraph) grapheme spans."""
    tricky = word_entry.get("tricky_letters") or []
    if tricky:
        return [[i] for i in tricky]
    word, phonemes = word_entry["word"], word_entry.get("phonemes", [])
    return [g for g in phoneme_letter_groups(word, phonemes) if len(g) > 1]


# --------------------------------------------------------------- payload builders
def _payload_word_builder(word_entry: dict, distractor_pool: list[str]) -> dict:
    """Tiles (phoneme graphemes + distractors) that tap into sound boxes."""
    phonemes = word_entry.get("phonemes") or list(word_entry["word"])
    tiles = list(phonemes) + list(word_entry.get("distractors") or distractor_pool[:2])
    sound_boxes = [{"width": "digraph" if len(p) > 1 else "single"} for p in phonemes]
    return {"sound_boxes": sound_boxes, "tiles": tiles}


def _payload_letter_boxes(word_entry: dict) -> dict:
    """One input box per LETTER; phoneme_groups draw the digraph brackets."""
    word = word_entry["word"]
    phonemes = word_entry.get("phonemes") or list(word)
    return {
        "boxes": [{"count": 1} for _ in word],
        "phoneme_groups": phoneme_letter_groups(word, phonemes),
    }


def _payload_echo_dictation(word_entry: dict) -> dict:
    return {}


def _payload_missing_letters(word_entry: dict) -> dict:
    """The word shown with 1–2 letters blanked — the pattern letters if we know
    them (tricky ❤️ letters, else the multi-letter grapheme), else the first vowel.
    `display` carries the visible letters with None at the blanks (the child SEES
    the rest of the word by design)."""
    word = word_entry["word"]
    blanks = [i for group in _markers_for(word_entry) for i in group][:2]
    if not blanks:
        vowels = [i for i, ch in enumerate(word) if ch in "aeiou"]
        blanks = vowels[:1] or [len(word) // 2]
    display = [None if i in blanks else ch for i, ch in enumerate(word)]
    return {"display": display, "blanks": sorted(blanks)}


def _payload_word_sort(word_entry: dict) -> dict:
    """Sort THIS word into its pattern bucket vs a decoy. `correct_bucket` is
    stripped from the client view (server-graded)."""
    pattern = word_entry.get("pattern", "short_vowels")
    decoys = {
        "short_vowels": "magic_e", "digraphs": "short_vowels", "magic_e": "short_vowels",
        "vowel_teams": "short_vowels", "r_controlled": "short_vowels",
        "blends": "digraphs", "doubling_endings": "short_vowels",
        "suffixes": "short_vowels", "heart_words": "short_vowels",
    }
    labels = {
        "short_vowels": ("short vowel", "🔤"), "digraphs": ("two letters, one sound", "🤝"),
        "magic_e": ("magic e", "🪄"), "vowel_teams": ("vowel team", "👯"),
        "r_controlled": ("bossy r", "🦁"), "blends": ("blend", "🧩"),
        "doubling_endings": ("double ending", "👐"), "suffixes": ("ending", "🔚"),
        "heart_words": ("heart word", "❤️"),
    }
    decoy = decoys.get(pattern, "short_vowels")
    buckets = [
        {"id": b, "label": labels.get(b, (b, ""))[0], "emoji": labels.get(b, ("", ""))[1]}
        for b in (pattern, decoy)
    ]
    buckets.sort(key=lambda b: b["id"])  # stable order, not answer-revealing
    return {"chip": word_entry["word"], "buckets": buckets, "correct_bucket": pattern}


def _payload_heart_word_spotlight(word_entry: dict) -> dict:
    """Look–cover–write–check: the child SEES the word (by design), tricky letters
    marked ❤️, then covers it and types from memory."""
    word = word_entry["word"]
    tricky = word_entry.get("tricky_letters") or [
        i for i, ch in enumerate(word) if ch in "aeiou"
    ][:2]
    return {"display_word": word, "tricky_letters": tricky}


def _payload_phrase_dictation(word_entry: dict) -> dict:
    """She hears the phrase and types it one input per word; only the word lengths
    go to the client (for input sizing) — never the letters."""
    words = word_entry["word"].split()
    return {"word_lengths": [len(w) for w in words]}


def _payload_sentence_scribe(word_entry: dict) -> dict:
    return {"word_count": len(word_entry["word"].split())}


def _payload_bd_ninja(word_entry: dict) -> dict:
    """The b/d discrimination game. Client-scored (ADR-014 §4): a deterministic
    letter stream + how many targets it contains; the client reports hits/wrong."""
    rng = random.Random(word_entry.get("word", "bd"))
    target = rng.choice(["b", "d"])
    letters = [rng.choice([target] * 2 + ["b", "d", "p", "q"]) for _ in range(config.BD_NINJA_LETTERS)]
    if target not in letters:  # pragma: no cover — 2/3 weighting makes this ~impossible
        letters[0] = target
    return {"target_letter": target, "letters": letters, "goal": letters.count(target)}


_PAYLOAD_BUILDERS = {
    "word_builder": lambda w, pool: _payload_word_builder(w, pool),
    "letter_boxes": lambda w, pool: _payload_letter_boxes(w),
    "echo_dictation": lambda w, pool: _payload_echo_dictation(w),
    "missing_letters": lambda w, pool: _payload_missing_letters(w),
    "word_sort": lambda w, pool: _payload_word_sort(w),
    "heart_word_spotlight": lambda w, pool: _payload_heart_word_spotlight(w),
    "phrase_dictation": lambda w, pool: _payload_phrase_dictation(w),
    "sentence_scribe": lambda w, pool: _payload_sentence_scribe(w),
    "bd_ninja": lambda w, pool: _payload_bd_ninja(w),
}


# --------------------------------------------------------------- envelope builder
def build_item(
    exercise_type: str,
    skill_id: str,
    word_entry: dict,
    scaffold_level: int,
    *,
    distractor_pool: list[str] | None = None,
    source: str = "engine",
) -> dict:
    """Assemble a valid ADR-005 item envelope for one word."""
    if exercise_type not in EXERCISE_TYPES:
        raise ValueError(f"unknown exercise type: {exercise_type!r}")
    word = word_entry["word"]
    rule_id, why_text = why_for(skill_id, word_entry)
    payload = _PAYLOAD_BUILDERS[exercise_type](word_entry, distractor_pool or [])
    prompts = {
        "word_builder": "build the word",
        "letter_boxes": "type the word",
        "missing_letters": "fill in the missing letters",
        "word_sort": "which kind of word is it?",
        "heart_word_spotlight": "look… cover… write it!",
        "echo_dictation": "listen, then spell it",
        "phrase_dictation": "listen, then write each word",
        "sentence_scribe": "listen, then write the sentence",
        "bd_ninja": f"pop only the {payload.get('target_letter', 'b')}!",
    }
    grading = {"case_insensitive": True, "trim": True}
    if exercise_type in TEXT_TYPES:
        grading.update({"collapse_spaces": True, "ignore_punctuation": True})
    return {
        "contract_version": CONTRACT_VERSION,
        "item_id": str(uuid.uuid4()),
        "type": exercise_type,
        "skill_id": skill_id,
        "target": word,
        "prompt": {
            "text": prompts[exercise_type],
            "audio_word": word,
            "image_emoji": word_entry.get("emoji", ""),
            "auto_speak": exercise_type in ("echo_dictation", "phrase_dictation", "sentence_scribe"),
        },
        "payload": payload,
        "grading": grading,
        "scaffold_level": scaffold_level,
        "why": {"rule_id": rule_id, "text_fallback": why_text, "markers": _markers_for(word_entry)},
        "source": source,
    }


# --------------------------------------------------------------- grading
def normalize_answer(text: str, grading: dict) -> str:
    """Apply the item's grading flags to an answer/target for comparison. Multi-
    word targets are forgiving on case, extra spaces, and end punctuation — never
    punitive on mechanics she wasn't asked to master (invariant #3 spirit)."""
    out = text or ""
    if grading.get("trim", True):
        out = out.strip()
    if grading.get("case_insensitive", True):
        out = out.lower()
    if grading.get("ignore_punctuation"):
        out = re.sub(r"[.,!?;:'\"]", "", out)
    if grading.get("collapse_spaces"):
        out = " ".join(out.split())
    return out


# --------------------------------------------------------------- validation
_ENVELOPE_KEYS = {
    "contract_version", "item_id", "type", "skill_id", "target", "prompt",
    "payload", "grading", "scaffold_level", "why", "source",
}


def validate_item(item: dict) -> bool:
    """Structural validation (ADR-005). Anything the agent emits passes through
    here before use; a False result → the caller falls back to the engine item."""
    if not isinstance(item, dict) or not _ENVELOPE_KEYS <= set(item):
        return False
    if item["contract_version"] != CONTRACT_VERSION:
        return False
    if item["type"] not in EXERCISE_TYPES:
        return False
    if not isinstance(item.get("target"), str) or not item["target"]:
        return False
    payload = item.get("payload")
    if not isinstance(payload, dict):
        return False
    t = item["type"]
    checks = {
        "word_builder": lambda p: isinstance(p.get("tiles"), list) and isinstance(p.get("sound_boxes"), list),
        "letter_boxes": lambda p: isinstance(p.get("boxes"), list) and isinstance(p.get("phoneme_groups"), list),
        "echo_dictation": lambda p: True,
        "missing_letters": lambda p: isinstance(p.get("display"), list) and isinstance(p.get("blanks"), list),
        "word_sort": lambda p: isinstance(p.get("buckets"), list) and bool(p.get("chip")) and bool(p.get("correct_bucket")),
        "heart_word_spotlight": lambda p: bool(p.get("display_word")) and isinstance(p.get("tricky_letters"), list),
        "phrase_dictation": lambda p: isinstance(p.get("word_lengths"), list) and bool(p["word_lengths"]),
        "sentence_scribe": lambda p: isinstance(p.get("word_count"), int),
        "bd_ninja": lambda p: p.get("target_letter") in ("b", "d") and isinstance(p.get("letters"), list),
    }
    return checks[t](payload)


# Payload keys that are answer material — stripped from the client view per type.
_SECRET_PAYLOAD_KEYS = {"word_sort": ("correct_bucket",)}


def public_item(item: dict) -> dict:
    """The item as sent to the CLIENT — with `target`, the canned `why` text, and
    any answer-bearing payload keys stripped, so the answer key never reaches the
    browser (ADR-005: server-authoritative grading)."""
    safe = {k: v for k, v in item.items() if k != "target"}
    secret = _SECRET_PAYLOAD_KEYS.get(item["type"], ())
    if secret:
        safe["payload"] = {k: v for k, v in item["payload"].items() if k not in secret}
    safe["why"] = {"markers": item["why"]["markers"]}  # revealed only after an answer
    return safe


# --------------------------------------------------------------- agent tool schemas
def tool_schemas() -> list[dict]:
    """DeepSeek function-calling schemas — one tool per exercise type, generated
    from the same specs (ADR-012), so agent output is renderable by construction."""
    common = {
        "skill_id": {"type": "string"},
        "target": {"type": "string"},
        "emoji": {"type": "string"},
    }
    per_type_props: dict[str, dict] = {t: {} for t in EXERCISE_TYPES}
    per_type_props["word_builder"] = {"distractors": {"type": "array", "items": {"type": "string"}}}
    schemas = []
    for t in EXERCISE_TYPES:
        props = {**common, **per_type_props[t]}
        schemas.append(
            {
                "type": "function",
                "function": {
                    "name": f"emit_{t}",
                    "description": f"Produce a {t} exercise item for the given word.",
                    "parameters": {
                        "type": "object",
                        "properties": props,
                        "required": ["skill_id", "target"],
                    },
                },
            }
        )
    return schemas


def json_schema() -> dict:
    """Reference JSON-Schema rendering of the envelope (the `exercise.schema.json`
    artifact ADR-005 names). Not used for runtime validation (that's validate_item),
    but published so external tools/the design system can read the contract."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Spell Quest exercise item",
        "type": "object",
        "required": sorted(_ENVELOPE_KEYS),
        "properties": {
            "contract_version": {"const": CONTRACT_VERSION},
            "item_id": {"type": "string"},
            "type": {"enum": list(EXERCISE_TYPES)},
            "skill_id": {"type": "string"},
            "target": {"type": "string"},
            "prompt": {"type": "object"},
            "payload": {"type": "object"},
            "grading": {"type": "object"},
            "scaffold_level": {"type": "integer"},
            "why": {"type": "object"},
            "source": {"enum": ["engine", "agent"]},
        },
    }
