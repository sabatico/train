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


def band_for(effective_mastery: float) -> str:
    """low / mid / high mastery band (ADR-014 type policy)."""
    lo, hi = config.SCAFFOLD_CUTOFFS
    if effective_mastery < lo:
        return "low"
    return "mid" if effective_mastery < hi else "high"


def types_for(skill_id: str, band: str) -> tuple[str, ...]:
    """The exercise-type ROTATION for a skill at a mastery band (ADR-014 §2):
    variety within a session instead of one type repeated. Skill overrides first
    (heart words, b/d game, Strand D), else the band default."""
    override = config.TYPE_OVERRIDES.get(skill_id, {})
    return override.get(band) or config.TYPE_BANDS[band]


def make_content_provider(skills_doc: dict, words_for, today):
    """content(skill_id) -> list of word entries, for EVERY skill (ADR-014 §3).

    Skills with their own bank return it. The five bankless skills source from
    the introduced real banks: segmentation → any words; sequencing → LONG words;
    phrase/sentence dictation → the AI-enriched `phrase`/`sentence` fields;
    letter_orientation → synthetic b/d game rounds. Memoized per call."""
    skills = skills_doc["skills"]
    cache: dict[str, list] = {}

    def real_banks() -> list[dict]:
        pool: list[dict] = []
        for sid, s in skills.items():
            if s["introduced"] and sid not in config.CONTENT_FROM_OTHER_BANKS:
                pool.extend(words_for(sid))
        return pool

    def content(skill_id: str) -> list[dict]:
        if skill_id in cache:
            return cache[skill_id]
        if skill_id == "letter_orientation":
            # game rounds only when real content exists (never a games-only session)
            out = (
                [
                    {"word": f"bd-round-{i}", "difficulty": 1, "emoji": "⚔️", "kind": "game"}
                    for i in (1, 2, 3)
                ]
                if real_banks()
                else []
            )
        elif skill_id == "phoneme_segmentation":
            # only words whose sounds ARE their letters (heart words store sounds
            # like they→th/ay that can't be built/typed — owner-found bug)
            out = [
                w for w in real_banks()
                if len(w.get("phonemes") or []) >= 2
                and "".join(w["phonemes"]).lower() == w["word"].lower()
            ]
        elif skill_id == "word_sequencing":
            pool = [
                w for w in real_banks()
                if "".join(w.get("phonemes") or []).lower() == w["word"].lower()
            ]
            out = [w for w in pool if w.get("difficulty", 1) >= config.LONG_WORD_MIN_DIFFICULTY]
            if not out:
                out = [w for w in pool if len(w["word"]) >= 5]
        elif skill_id == "phrase_dictation":
            out = [
                {
                    "word": w["phrase"], "kind": "phrase", "emoji": w.get("emoji", ""),
                    "difficulty": min(5, len(w["phrase"].split()) + 1),
                }
                for w in real_banks()
                if w.get("phrase")
            ]
        elif skill_id == "sentence_writing":
            out = [
                {
                    "word": w["sentence"], "kind": "sentence", "emoji": w.get("emoji", ""),
                    "difficulty": min(5, len(w["sentence"].split()) + 1),
                }
                for w in real_banks()
                if w.get("sentence")
            ]
        else:
            out = words_for(skill_id)
        cache[skill_id] = out
        return out

    return content


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


_BAND_LEVEL = {"low": 1, "mid": 2, "high": 3}


def _entry(
    skill_id: str, word: dict, skills_doc: dict, today: date, slot: str, rotation_idx: int = 0
) -> dict:
    """One plan entry; the exercise type comes from the skill/band ROTATION
    (ADR-014 §2) so consecutive items on the same skill vary."""
    eff = skills_mod.effective_mastery(skills_doc["skills"][skill_id], today)
    band = band_for(eff)
    rotation = types_for(skill_id, band)
    ex_type = rotation[rotation_idx % len(rotation)]
    if slot == "warmup" and not word.get("kind"):
        ex_type = "letter_boxes"  # warm-ups on real words stay easy wins regardless of band
    return {
        "skill_id": skill_id,
        "word": word,
        "scaffold_level": _BAND_LEVEL[band],
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
    content = make_content_provider(skills_doc, words_for, today)

    def eff(sid: str) -> float:
        return skills_mod.effective_mastery(skills[sid], today)

    introduced = [s for s in skills_mod.introduced_skills(skills_doc) if content(s)]
    if not introduced:
        return []

    # the lesson focus is a TEACHABLE pattern (the b/d mini-game is capped practice,
    # never the focus — six identical game rounds is the monotony ADR-014 kills)
    focusable = [s for s in introduced if s not in config.FOCUS_EXCLUDED] or introduced
    focus = skills_mod.weakest_introduced({"skills": {s: skills[s] for s in focusable}}, today)
    # rotation counter per skill → consecutive items on a skill VARY in type
    rot: dict[str, int] = {}

    def add(bag: list, sid: str, slot: str, used: set[str], target: int | None):
        if sid in config.FOCUS_EXCLUDED and rot.get(sid, 0) >= config.GAME_ITEMS_MAX:
            return False  # one game round per session is plenty
        w = _pick_word(sid, content, rng, used, target)
        if w:
            used.add(w["word"])
            bag.append(_entry(sid, w, skills_doc, today, slot, rot.get(sid, 0)))
            rot[sid] = rot.get(sid, 0) + 1
            return True
        return False

    # reserve one slot for the challenge when the child has unlocked Strand D
    challenge_sid = next(
        (s for s in ("sentence_writing", "phrase_dictation") if skills[s]["introduced"] and content(s)),
        None,
    )
    challenge_count = config.CHALLENGE_ITEMS if challenge_sid else 0
    warmup_count = min(config.WARMUP_ITEMS, n)
    middle_target = max(1, n - warmup_count - challenge_count)
    n_focus, n_review, n_stretch = _counts(middle_target)
    used: set[str] = set()
    middle: list[dict] = []

    # focus: the weakest introduced skill (the session's pattern)
    for _ in range(n_focus):
        add(middle, focus, "focus", used, target_difficulty(eff(focus)))

    # review: other introduced skills, most-decayed first (spiral review)
    review_pool = sorted((s for s in introduced if s != focus), key=eff)
    for i in range(n_review):
        if not review_pool:
            break
        sid = review_pool[i % len(review_pool)]
        add(middle, sid, "review", used, target_difficulty(eff(sid)))

    # stretch: the next not-yet-introduced skill whose prereqs are met (a teaser)
    stretch_sid = next(
        (
            s
            for s in skills
            if not skills[s]["introduced"]
            and content(s)
            and skills_mod.prerequisites_met(s, skills, graph, today)
        ),
        None,
    )
    for _ in range(n_stretch):
        sid = stretch_sid or focus
        add(middle, sid, "stretch" if stretch_sid else "review", used, target_difficulty(eff(sid)))

    # top up from the focus skill so the session is always full
    while len(middle) < middle_target:
        if not add(middle, focus, "focus", used, target_difficulty(eff(focus))):
            break  # pragma: no cover — focus ∈ introduced-with-content

    # warm-up: easy wins from the strongest REAL-WORD skills (never a game or a
    # phrase — the first taps of the day must be guaranteed easy)
    warm_candidates = [
        s for s in introduced if s not in config.CONTENT_FROM_OTHER_BANKS
    ] or focusable
    warm_pool = sorted(warm_candidates, key=eff, reverse=True)
    warmup: list[dict] = []
    warm_used: set[str] = set()
    for i in range(warmup_count):
        add(warmup, warm_pool[i % len(warm_pool)], "warmup", warm_used, 1)

    plan = warmup + middle

    # never end the PRACTICE stretch on a struggle: if the last practice item's
    # skill is weak, move a strong item to the end (ADR-007 rule 6 spirit).
    if plan and eff(plan[-1]["skill_id"]) < config.WARMUP_MASTERY:
        strong_idx = next(
            (i for i in range(len(plan) - 1) if eff(plan[i]["skill_id"]) >= config.WARMUP_MASTERY),
            None,
        )
        if strong_idx is not None:
            plan.append(plan.pop(strong_idx))

    # the CHALLENGE caps the session (PLAN §7 step 5) — a phrase or sentence to
    # write, skippable without penalty; only once Strand D has unlocked.
    if challenge_sid:
        add(plan, challenge_sid, "challenge", used, target_difficulty(eff(challenge_sid)))
    return plan
