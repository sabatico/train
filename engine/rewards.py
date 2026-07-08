"""Rewards & gamification economy (ADR-011).

The load-bearing invariant (#3): rewards are ONLY ever added to — no operation
here decreases stars, XP, level, or removes a hatched creature. This is a testable
property. Level tracks *effort* (cumulative stars), deliberately decoupled from the
decaying skill mastery, so a bad week never demotes her.
"""
from __future__ import annotations

from datetime import date, timedelta

from . import config, skills as skills_mod


def stars_for(correct: bool, corrected: bool = False) -> int:
    """Stars for one item: 2 first-try, 1 if correct after the correction routine,
    0 on an unresolved miss. Never negative (ADR-011 / invariant #3)."""
    if correct and not corrected:
        return config.STARS_FIRST_TRY
    if correct and corrected:
        return config.STARS_AFTER_CORRECTION
    return 0


def add_stars(rewards: dict, stars: int) -> dict:
    """Add stars and recompute xp/level/level_name. `stars` must be ≥ 0 — a
    negative value is a bug and is rejected (invariant #3 is enforced, not hoped)."""
    if stars < 0:
        raise ValueError("rewards are add-only (invariant #3): stars must be >= 0")
    rewards["stars_total"] += stars
    rewards["xp"] = rewards["stars_total"]        # xp == stars (legible to a 7-yo)
    rewards["level"] = config.level_for_xp(rewards["xp"])
    rewards["level_name"] = config.level_name(rewards["level"])
    return rewards


def _bump_streak(rewards: dict, today: date) -> None:
    """Daily streak with freeze tokens (ADR-011). A finished session on a new day
    extends the flame; a one-day gap auto-spends a freeze; a longer gap (no freeze)
    quietly resets to 1 — never a punitive screen."""
    streak = rewards["streak"]
    last = streak.get("last_day")
    if last == today.isoformat():
        return  # already counted a session today
    if last is None:
        streak["count"] = 1
    else:
        gap = (today - date.fromisoformat(last)).days
        if gap == 1:
            streak["count"] += 1
        elif gap > 1:
            missed = gap - 1
            if streak["freezes"] >= missed:
                streak["freezes"] -= missed
                streak["count"] += 1
            else:
                streak["count"] = 1  # warm reset, no shame
    streak["last_day"] = today.isoformat()
    # earn a freeze every 5-day milestone, capped at 2
    if streak["count"] % 5 == 0 and streak["freezes"] < 2:
        streak["freezes"] += 1


def hatch_creatures(
    rewards: dict,
    skills_doc: dict,
    previous_masteries: dict[str, float],
    today: date,
) -> list[str]:
    """Hatch a creature for each skill that is 'mastered' (effective ≥ 85) now AND
    was ≥ 85 at the end of the previous session (sustained over ≥2 sessions,
    ADR-007/011). A hatched creature is permanent — decay never un-hatches it
    (invariant #3). Returns the skill ids that hatched this call."""
    already = {c["skill_id"] for c in rewards["collection"]}
    hatched: list[str] = []
    for sid, skill in skills_doc["skills"].items():
        if sid in already:
            continue
        now = skills_mod.effective_mastery(skill, today)
        prev = previous_masteries.get(sid, 0.0)
        if now >= config.MASTERY_THRESHOLD and prev >= config.MASTERY_THRESHOLD:
            rewards["collection"].append(
                {"skill_id": sid, "creature_id": f"creature_{sid}", "hatched_on": today.isoformat()}
            )
            hatched.append(sid)
    return hatched


def apply_session_end(
    rewards: dict,
    skills_doc: dict,
    previous_masteries: dict[str, float],
    today: date,
) -> dict:
    """Finish-of-session rewards bookkeeping: streak + creature hatching. Stars are
    added per item during the session via add_stars(); this handles the once-per-
    session effects. Returns the (mutated) rewards."""
    _bump_streak(rewards, today)
    hatch_creatures(rewards, skills_doc, previous_masteries, today)
    return rewards
