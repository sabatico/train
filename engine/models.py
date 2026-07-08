"""Default record shapes for the file store (ADR-006).

Plain dict factories (JSON-native, no ORM per ADR-001). Each returns a FRESH
object every call so callers can never accidentally share mutable defaults.
The store (`store.py`) is the only module that persists these.
"""
from __future__ import annotations

from . import config


def default_profile() -> dict:
    return {
        "display_name": "friend",
        "avatar": "panda",
        "settings": {
            "tts_voice": None,        # None → browser default (parent sets in PAR-04)
            "tts_rate": 0.9,          # slightly slow for dictation
            "font_scale": 1.0,
            "items_per_session": config.ITEMS_PER_SESSION,
        },
    }


def default_skill(skill_id: str, introduced: bool) -> dict:
    """One skill record (ADR-006/007).

    `mastery` is the value *as of `last_practiced`*; effective mastery is computed
    lazily elsewhere (ADR-007 rule 3) — never persisted per read.
    """
    return {
        "id": skill_id,
        "mastery": config.INITIAL_MASTERY if introduced else 0,
        "last_practiced": None,       # ISO date; None = never practiced
        "exposures": 0,
        "streak": 0,
        "introduced": introduced,     # one-way latch (ADR-007 rule 4)
        "decay_per_day": config.SKILLS[skill_id],
    }


def default_skills(skill_graph: dict[str, list[str]]) -> dict:
    """All 14 skills. A skill is introduced at bootstrap iff it has no prerequisites
    (empty prereqs ⇒ the ADR-007 gate is vacuously met)."""
    skills = {}
    for skill_id in config.SKILL_IDS:
        prereqs = skill_graph.get(skill_id, [])
        skills[skill_id] = default_skill(skill_id, introduced=not prereqs)
    return {"skills": skills}


def default_rewards() -> dict:
    return {
        "stars_total": 0,
        "xp": 0,
        "level": 1,
        "level_name": config.level_name(1),
        "streak": {"count": 0, "last_day": None, "freezes": 0},
        "collection": [],             # [{skill_id, creature_id, hatched_on}]
    }
