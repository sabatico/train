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

import uuid

CONTRACT_VERSION = 1

# The exercise types this contract knows. Phase-1 ships the first three; the rest
# are declared so payload builders/registry can grow without a version bump
# (additive per ADR-005). Order mirrors PLAN §3.
EXERCISE_TYPES = ("word_builder", "letter_boxes", "echo_dictation")

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


_PAYLOAD_BUILDERS = {
    "word_builder": lambda w, pool: _payload_word_builder(w, pool),
    "letter_boxes": lambda w, pool: _payload_letter_boxes(w),
    "echo_dictation": lambda w, pool: _payload_echo_dictation(w),
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
    return {
        "contract_version": CONTRACT_VERSION,
        "item_id": str(uuid.uuid4()),
        "type": exercise_type,
        "skill_id": skill_id,
        "target": word,
        "prompt": {
            "text": "spell the word",
            "audio_word": word,
            "image_emoji": word_entry.get("emoji", ""),
            "auto_speak": exercise_type == "echo_dictation",
        },
        "payload": payload,
        "grading": {"case_insensitive": True, "trim": True},
        "scaffold_level": scaffold_level,
        "why": {"rule_id": rule_id, "text_fallback": why_text, "markers": _markers_for(word_entry)},
        "source": source,
    }


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
    if t == "word_builder":
        return isinstance(payload.get("tiles"), list) and isinstance(payload.get("sound_boxes"), list)
    if t == "letter_boxes":
        return isinstance(payload.get("boxes"), list) and isinstance(payload.get("phoneme_groups"), list)
    if t == "echo_dictation":
        return True
    return False  # pragma: no cover — unreachable: t is constrained to EXERCISE_TYPES above


def public_item(item: dict) -> dict:
    """The item as sent to the CLIENT — with `target` and the canned `why` text
    stripped, so the answer key never reaches the browser (ADR-005: server-
    authoritative grading; a curious kid can't read answers in devtools)."""
    safe = {k: v for k, v in item.items() if k != "target"}
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
    per_type_props = {
        "word_builder": {"distractors": {"type": "array", "items": {"type": "string"}}},
        "letter_boxes": {},
        "echo_dictation": {},
    }
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
