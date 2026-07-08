"""Session lifecycle & assembly (ADR-009).

Stateless per request (ADR-004): in-flight state lives in `sessions/current.json`,
loaded → mutated → atomically saved each call, so a refresh or a wandered-off
7-year-old can resume and nothing is lost. Grading is SERVER-authoritative
(ADR-005): the browser never sees the target or decides correctness.

Ties the deterministic engine together: selector (what) → contracts (how it's
shown) → classifier (what the error means) → skills (mastery) → rewards.
"""
from __future__ import annotations

import random
import uuid
from datetime import date

from agent import teacher
from . import classifier, config, contracts, rewards, selector, skills as skills_mod, store


# --------------------------------------------------------------- helpers
def _today(today: date | None) -> date:
    return today or date.today()


def _normalize(text: str, grading: dict) -> str:
    if grading.get("trim", True):
        text = text.strip()
    if grading.get("case_insensitive", True):
        text = text.lower()
    return text


def _build_teach(focus_skill: str, words_for) -> dict:
    """The one mini-lesson card for the session's focus pattern (PLAN §7 step 3).
    The rule is generated from the FIRST example word so it sounds out that word."""
    words = words_for(focus_skill)
    example = words[0] if words else {"word": focus_skill, "phonemes": []}
    rule_id, text = contracts.why_for(focus_skill, example)
    return {
        "skill_id": focus_skill,
        "rule_id": rule_id,
        "text": text,
        "examples": [w["word"] for w in words[:2]],
    }


def _public_state(state: dict) -> dict:
    """The session view sent to the client (no answer keys)."""
    cursor = state["cursor"]
    items = state["items"]
    item_view = contracts.public_item(items[cursor]["item"]) if cursor < len(items) else None
    # Compute the teach card FRESH from the focus skill on every read (not from a
    # value baked into current.json at start), so content fixes apply immediately
    # even to a session already in progress.
    focus = state.get("focus_skill")
    teach = _build_teach(focus, store.load_word_bank) if focus else None
    return {
        "session_id": state["session_id"],
        "focus_skill": state["focus_skill"],
        "teach": teach,
        "cursor": cursor,
        "total_items": len(items),
        "done": cursor >= len(items),
        "item": item_view,
        "totals": state["totals"],
    }


# --------------------------------------------------------------- start
def start_session(
    student_id: str, today: date | None = None, rng: random.Random | None = None
) -> dict:
    """Begin (or resume) a session. If a current session from today exists, resume
    it; a stale (earlier-day) one is discarded and a fresh plan built (ADR-009)."""
    day = _today(today)
    existing = store.load_current_session(student_id)
    if existing and existing.get("date") == day.isoformat():
        return _public_state(existing)  # resume from cursor

    skills_doc = store.load(student_id, "skills")
    graph = store.load_skill_graph()
    plan = selector.build_plan(skills_doc, graph, store.load_word_bank, day, rng=rng)

    items = []
    for entry in plan:
        word = entry["word"]
        item = contracts.build_item(
            entry["exercise_type"], entry["skill_id"], word, entry["scaffold_level"]
        )
        items.append(
            {
                "item": item,
                "word": word,
                "skill_id": entry["skill_id"],
                "attempts": [],
                "stars": 0,
                "resolved": False,
                "misses": 0,
            }
        )

    # Focus = the weakest introduced skill THAT HAS CONTENT — must match what the
    # selector actually built the plan around (else the teach card names a skill
    # with no items). Skills without a word bank yet can't be a session focus.
    with_words = {
        sid: s
        for sid, s in skills_doc["skills"].items()
        if s["introduced"] and store.load_word_bank(sid)
    }
    focus = skills_mod.weakest_introduced({"skills": with_words}, day) if with_words else None
    state = {
        "session_id": str(uuid.uuid4()),
        "date": day.isoformat(),
        "focus_skill": focus,
        "cursor": 0,
        "items": items,
        "totals": {"stars": 0, "items": len(items), "correct_first_try": 0},
        "consecutive_misses": 0,
    }
    store.save_current_session(student_id, state)
    return _public_state(state)


def get_item(student_id: str) -> dict | None:
    state = store.load_current_session(student_id)
    if not state:
        return None
    return _public_state(state)


# --------------------------------------------------------------- answer
def submit_answer(
    student_id: str,
    item_id: str,
    attempt: str,
    phase: str = "first",
    today: date | None = None,
) -> dict:
    """Grade one answer server-side, classify a miss, update mastery, advance.

    On a first-try miss: hold the cursor, return the reveal (correct word + markers
    + why + audio) so the UI runs the correction routine, next="retry". On the
    retype: score it and advance. Never traps the child — a wrong retry still
    advances (she has seen the correct word)."""
    day = _today(today)
    state = store.load_current_session(student_id)
    if not state:
        return {"error": "no_active_session"}
    cursor = state["cursor"]
    if cursor >= len(state["items"]):
        return {"error": "session_complete"}

    entry = state["items"][cursor]
    item = entry["item"]
    if item["item_id"] != item_id:
        return {"error": "item_mismatch", "expected": item["item_id"]}

    target = item["target"]
    grading = item["grading"]
    correct = _normalize(attempt, grading) == _normalize(target, grading)
    is_heart = entry["skill_id"] == "heart_words"
    result = classifier.classify(
        attempt, target, is_heart_word=is_heart, target_phonemes=entry["word"].get("phonemes")
    )
    entry["attempts"].append(
        {"attempt": attempt, "phase": phase, "correct": correct, "tags": result["tags"]}
    )

    corrected = phase != "first"
    score = skills_mod.score_for(correct, corrected=corrected)
    stars = rewards.stars_for(correct, corrected=corrected)

    # first-try miss → correction routine, hold position
    if not correct and not corrected:
        entry["misses"] += 1
        state["consecutive_misses"] += 1
        _maybe_step_down(state)
        store.save_current_session(student_id, state)
        # kid-voice explanation from the agent, or the canned line on any failure
        # (ADR-012 / invariant #2: only word + tag + rule id go to the prompt).
        # Generated FRESH from THIS word's sounds (contracts.why_for) — e.g.
        # "Sound out each letter: /p/ /u/ /p/ → pup" — not a static baked template.
        rule_id, canned = contracts.why_for(entry["skill_id"], entry["word"])
        why = teacher.feedback_for(target, result["primary"], rule_id, canned)
        return {
            "correct": False,
            "stars": 0,
            "tags": result["tags"],
            "primary": result["primary"],
            "reveal": {
                "target": target,
                "markers": item["why"]["markers"],
                "why": why,
                "audio": target,
            },
            "next": "retry",
        }

    # resolved (correct first try, or the retype): score mastery + advance
    _apply_mastery(student_id, entry["skill_id"], score, day)
    entry["stars"] = stars
    entry["resolved"] = True
    state["totals"]["stars"] += stars
    if correct and not corrected:
        state["totals"]["correct_first_try"] += 1
        state["consecutive_misses"] = 0
    state["cursor"] += 1
    store.save_current_session(student_id, state)
    return {
        "correct": correct,
        "stars": stars,
        "tags": result["tags"],
        "next": "advance",
        "done": state["cursor"] >= len(state["items"]),
        "totals": state["totals"],
    }


def _apply_mastery(student_id: str, skill_id: str, score: float, day: date) -> None:
    skills_doc = store.load(student_id, "skills")
    skill = skills_doc["skills"].get(skill_id)
    if skill is None:
        return
    skills_mod.update_mastery(skill, score, day)
    store.save(student_id, "skills", skills_doc)


def _maybe_step_down(state: dict) -> None:
    """Two consecutive FIRST-TRY misses → make the NEXT unanswered item easier
    (ADR-007 rule 6): drop it to the most-scaffolded exercise type and reset the
    counter. 'Consecutive misses' counts first-try failures — a correct *retype*
    does NOT clear the count, because a first-try miss means the difficulty was
    too high regardless of whether she could then copy the revealed word. Only a
    correct first-try answer resets it (see submit_answer)."""
    if state["consecutive_misses"] < 2:
        return
    nxt = state["cursor"] + 1
    if nxt < len(state["items"]):
        entry = state["items"][nxt]
        easiest = config.SCAFFOLD_TYPES[0]
        entry["item"] = contracts.build_item(easiest, entry["skill_id"], entry["word"], 1)
    state["consecutive_misses"] = 0


# --------------------------------------------------------------- finish
def finish_session(student_id: str, today: date | None = None) -> dict:
    """Close the session: unlock newly-eligible skills, apply streak + hatching,
    write the completed log, clear current (ADR-009)."""
    day = _today(today)
    state = store.load_current_session(student_id)
    if not state:
        return {"error": "no_active_session"}

    skills_doc = store.load(student_id, "skills")
    graph = store.load_skill_graph()
    newly = skills_mod.update_introductions(skills_doc, graph, day)
    store.save(student_id, "skills", skills_doc)

    end_masteries = {
        sid: skills_mod.effective_mastery(s, day) for sid, s in skills_doc["skills"].items()
    }
    previous = _previous_end_masteries(student_id)

    rewards_doc = store.load(student_id, "rewards")
    hatched = rewards.hatch_creatures(rewards_doc, skills_doc, previous, day)
    rewards.apply_session_end(rewards_doc, skills_doc, previous, day)
    store.save(student_id, "rewards", rewards_doc)

    log = {
        "student_id": student_id,
        "date": state["date"],
        "session_id": state["session_id"],
        "focus_skill": state["focus_skill"],
        "totals": state["totals"],
        "items": [
            {
                "item_id": e["item"]["item_id"],
                "type": e["item"]["type"],
                "skill_id": e["skill_id"],
                "target": e["item"]["target"],
                "attempts": e["attempts"],
                "stars": e["stars"],
            }
            for e in state["items"]
        ],
        "end_masteries": end_masteries,
    }
    store.write_session_log(student_id, log, on=day)
    # append a dated observation to the teacher notebook (PAR-03). Deterministic
    # summary for now; agent-written weekly notes are a later enrichment (T-004).
    t = state["totals"]
    store.append_memory(
        student_id,
        f"Focus '{state['focus_skill']}': {t['correct_first_try']}/{t['items']} first try, "
        f"{t['stars']} stars." + (f" Newly introduced: {', '.join(newly)}." if newly else ""),
        on=day,
    )
    store.clear_current_session(student_id)

    return {
        "stars": state["totals"]["stars"],
        "correct_first_try": state["totals"]["correct_first_try"],
        "total_items": state["totals"]["items"],
        "level": rewards_doc["level"],
        "level_name": rewards_doc["level_name"],
        "streak": rewards_doc["streak"],
        "newly_introduced": newly,
        "hatched": hatched,
    }


def _previous_end_masteries(student_id: str) -> dict[str, float]:
    """The `end_masteries` from the most recent completed session (for the
    sustained-mastery hatch check, ADR-011). Empty if there is no prior session."""
    for date_key in reversed(store.list_session_logs(student_id)):
        log = store.load_session_log(student_id, date_key)
        if log and "end_masteries" in log:
            return log["end_masteries"]
    return {}
