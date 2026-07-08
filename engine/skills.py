"""The mastery model — the rose of winds (ADR-007).

Pure functions over the skill records defined in ADR-006. No IO, no randomness,
no wall clock (the caller passes `today`) — so it is fully deterministic and the
highest-value test target in the engine. The AI agent never computes mastery; it
only narrates what this module decides (ADR-002/012).

Key idea (ADR-007 rule 3): the stored `mastery` is the value *as of
`last_practiced`*. The value used everywhere else is the **effective** mastery,
a lazy projection that subtracts decay for the days since — computed on read,
never persisted per read (which would compound).
"""
from __future__ import annotations

from datetime import date

from . import config


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def effective_mastery(skill: dict, today: date) -> float:
    """Decayed mastery as of `today` (ADR-007 rule 3). Idempotent: depends only on
    the stored baseline + elapsed days, so calling it twice never over-decays."""
    base = float(skill["mastery"])
    last = skill.get("last_practiced")
    if not last:
        return base  # never practiced → the baseline stands (no decay from nothing)
    days = (today - date.fromisoformat(last)).days
    if days <= 0:
        return base
    return _clamp(base - float(skill["decay_per_day"]) * days)


def score_for(correct: bool, corrected: bool = False) -> float:
    """Map an answer outcome to a learning score (ADR-007 rule 1).

    correct first try → 1.0; correct only after the correction routine → 0.5;
    miss → 0.0 (the retype-it-right step teaches, but doesn't count as mastery)."""
    if correct and not corrected:
        return config.SCORE_FIRST_TRY
    if correct and corrected:
        return config.SCORE_AFTER_CORRECTION
    return config.SCORE_MISS


def update_mastery(skill: dict, score: float, today: date) -> dict:
    """Apply one graded result to a skill IN PLACE and return it (ADR-007 rule 2).

    EMA starts from the *effective* (decayed) mastery so a long gap is felt, then
    writes the new baseline with `last_practiced = today`. The learning rate slows
    as exposures accrue, so one bad day can't wipe a well-practised skill."""
    eff = effective_mastery(skill, today)
    k = config.k_for_exposures(skill["exposures"])
    skill["mastery"] = _clamp(eff + k * (100.0 * score - eff))
    skill["last_practiced"] = today.isoformat()
    skill["exposures"] += 1
    skill["streak"] = skill["streak"] + 1 if score >= config.SCORE_FIRST_TRY else 0
    return skill


def is_mastered(skill: dict, today: date) -> bool:
    """Effective mastery at or above the mastery threshold (ADR-007). The
    'sustained over ≥2 sessions' guard for hatching a creature lives in the
    rewards/session layer (it needs session history), not here."""
    return effective_mastery(skill, today) >= config.MASTERY_THRESHOLD


def prerequisites_met(skill_id: str, skills: dict, graph: dict, today: date) -> bool:
    """True when every prerequisite's EFFECTIVE mastery clears the unlock
    threshold (ADR-007 rule 4). Empty prereqs ⇒ vacuously met."""
    for prereq in graph.get(skill_id, []):
        prereq_skill = skills.get(prereq)
        if prereq_skill is None:
            return False
        if effective_mastery(prereq_skill, today) < config.UNLOCK_THRESHOLD:
            return False
    return True


def update_introductions(skills_doc: dict, graph: dict, today: date) -> list[str]:
    """Latch any newly unlockable skills to `introduced` (a ONE-WAY change —
    ADR-007 rule 4). Call at SESSION END so a lucky mid-session streak can't
    prematurely unlock. A skill introduced for the first time gets the starting
    mastery credit (config.INITIAL_MASTERY) instead of a demoralizing 0.

    Returns the ids newly introduced this call (for the UI's 'new skill!' moment).
    """
    skills = skills_doc["skills"]
    newly: list[str] = []
    for skill_id, skill in skills.items():
        if skill["introduced"]:
            continue
        if prerequisites_met(skill_id, skills, graph, today):
            skill["introduced"] = True
            if skill["mastery"] < config.INITIAL_MASTERY:
                skill["mastery"] = config.INITIAL_MASTERY
            newly.append(skill_id)
    return newly


def introduced_skills(skills_doc: dict) -> list[str]:
    return [sid for sid, s in skills_doc["skills"].items() if s["introduced"]]


def weakest_introduced(skills_doc: dict, today: date) -> str | None:
    """The lowest effective-mastery introduced skill — the session's focus
    pattern (ADR-007 rule 5, the 60% slot)."""
    intro = introduced_skills(skills_doc)
    if not intro:
        return None
    skills = skills_doc["skills"]
    return min(intro, key=lambda sid: effective_mastery(skills[sid], today))
