"""Adaptive item selector — decides what she practises next (ADR-007 rule 5).

Deterministic given its inputs (randomness is injected via an rng argument so
tests can seed it). Produces an ordered list of *plan entries* — abstract
{skill_id, word, scaffold_level, exercise_type, slot} — which the session builder
(ADR-009) wraps into the ADR-005 exercise envelopes. The agent may reorder a plan
(ADR-012) but never changes these rules.
"""
from __future__ import annotations

import random
from datetime import date

from . import config, skills as skills_mod


def scaffold_for(effective_mastery: float) -> tuple[int, str]:
    """Map effective mastery to (scaffold_level, exercise_type) via the ladder —
    lower mastery ⇒ more scaffolding, aiming ~80% success (ADR-007)."""
    idx = 0
    for cut in config.SCAFFOLD_CUTOFFS:
        if effective_mastery >= cut:
            idx += 1
    idx = min(idx, len(config.SCAFFOLD_TYPES) - 1)
    return idx + 1, config.SCAFFOLD_TYPES[idx]


def _counts(n: int) -> tuple[int, int, int]:
    """Split n items into (focus, review, stretch) by the 60/30/10 mix."""
    focus = round(n * config.MIX_FOCUS)
    review = round(n * config.MIX_REVIEW)
    stretch = max(0, n - focus - review)
    return focus, review, stretch


def target_difficulty(effective_mastery: float) -> int:
    """Map mastery to a target word difficulty (1–5): a shakier skill gets easier
    words, a stronger one gets harder words. mastery 0→1 … 100→5."""
    return 1 + round(4 * max(0.0, min(100.0, effective_mastery)) / 100.0)


def _pick_word(
    skill_id: str,
    words_for,
    rng: random.Random,
    used: set[str],
    target: int | None = None,
) -> dict | None:
    """Choose an unused word for a skill, or None if the bank is empty/exhausted.
    When `target` is given, prefer words whose difficulty is closest to it (so word
    complexity tracks her mastery); ties broken randomly. Without a target, random."""
    bank = [w for w in words_for(skill_id) if w.get("word") not in used]
    if not bank:
        bank = words_for(skill_id)  # allow reuse rather than starve the session
    if not bank:
        return None
    if target is None:
        return rng.choice(bank)
    best = min(abs(w.get("difficulty", 3) - target) for w in bank)
    closest = [w for w in bank if abs(w.get("difficulty", 3) - target) == best]
    return rng.choice(closest)


def _entry(skill_id: str, word: dict, skills_doc: dict, today: date, slot: str) -> dict:
    eff = skills_mod.effective_mastery(skills_doc["skills"][skill_id], today)
    level, ex_type = scaffold_for(eff)
    return {
        "skill_id": skill_id,
        "word": word,
        "scaffold_level": level,
        "exercise_type": ex_type,
        "slot": slot,
    }


def build_plan(
    skills_doc: dict,
    graph: dict,
    words_for,
    today: date,
    *,
    n: int | None = None,
    rng: random.Random | None = None,
) -> list[dict]:
    """Build the ordered session plan (ADR-007 rule 5).

    `words_for(skill_id) -> list[word dict]` supplies content (store.load_word_bank).
    Order: warm-up wins first, focus/review/stretch mixed in the middle, and a
    guaranteed win last (never end on a struggle)."""
    rng = rng or random.Random()
    n = n or config.ITEMS_PER_SESSION
    skills = skills_doc["skills"]

    def eff(sid: str) -> float:
        return skills_mod.effective_mastery(skills[sid], today)

    introduced = [s for s in skills_mod.introduced_skills(skills_doc) if words_for(s)]
    if not introduced:
        return []

    focus = skills_mod.weakest_introduced({"skills": {s: skills[s] for s in introduced}}, today)
    warmup_count = min(config.WARMUP_ITEMS, n)
    middle_target = n - warmup_count
    n_focus, n_review, n_stretch = _counts(middle_target)
    used: set[str] = set()
    middle: list[dict] = []

    # focus: the weakest introduced skill (the session's pattern)
    for _ in range(n_focus):
        w = _pick_word(focus, words_for, rng, used, target_difficulty(eff(focus)))
        if w:
            used.add(w["word"])
            middle.append(_entry(focus, w, skills_doc, today, "focus"))

    # review: other introduced skills, most-decayed first (spiral review)
    review_pool = sorted(
        (s for s in introduced if s != focus), key=eff  # lowest effective first
    )
    for i in range(n_review):
        if not review_pool:
            break
        sid = review_pool[i % len(review_pool)]
        w = _pick_word(sid, words_for, rng, used, target_difficulty(eff(sid)))
        if w:
            used.add(w["word"])
            middle.append(_entry(sid, w, skills_doc, today, "review"))

    # stretch: the next not-yet-introduced skill whose prereqs are met (a teaser),
    # else an extra review item
    stretch_sid = next(
        (
            s
            for s in skills
            if not skills[s]["introduced"]
            and words_for(s)
            and skills_mod.prerequisites_met(s, skills, graph, today)
        ),
        None,
    )
    for _ in range(n_stretch):
        sid = stretch_sid or focus
        slot = "stretch" if stretch_sid else "review"
        w = _pick_word(sid, words_for, rng, used, target_difficulty(eff(sid)))
        if w:
            used.add(w["word"])
            middle.append(_entry(sid, w, skills_doc, today, slot))

    # top up to the middle target from the focus skill if review/stretch couldn't
    # fill (e.g. only one skill has a word bank yet) — the session still gets full.
    while len(middle) < middle_target:
        w = _pick_word(focus, words_for, rng, used, target_difficulty(eff(focus)))
        if not w:  # pragma: no cover — focus ∈ introduced, which is filtered to skills with words
            break
        used.add(w["word"])
        middle.append(_entry(focus, w, skills_doc, today, "focus"))

    # warm-up: draw the first items from the strongest introduced skills (wins)
    warm_pool = sorted(introduced, key=eff, reverse=True)
    warmup: list[dict] = []
    warm_used: set[str] = set()
    for i in range(warmup_count):
        sid = warm_pool[i % len(warm_pool)]
        w = _pick_word(sid, words_for, rng, warm_used, target=1)  # easiest words = sure early wins
        if w:
            warm_used.add(w["word"])
            warmup.append(_entry(sid, w, skills_doc, today, "warmup"))

    plan = warmup + middle

    # never end on a struggle: if the last item's skill is weak, move a strong
    # (warm-up-grade) item to the end (ADR-007 rule 6 spirit).
    if plan and eff(plan[-1]["skill_id"]) < config.WARMUP_MASTERY:
        strong_idx = next(
            (i for i in range(len(plan) - 1) if eff(plan[i]["skill_id"]) >= config.WARMUP_MASTERY),
            None,
        )
        if strong_idx is not None:
            plan.append(plan.pop(strong_idx))
    return plan
