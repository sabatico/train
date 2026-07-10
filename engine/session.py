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
from . import classifier, config, contracts, phonics, rewards, selector, skills as skills_mod, store


# --------------------------------------------------------------- helpers
def _today(today: date | None) -> date:
    return today or date.today()


def _normalize(text: str, grading: dict) -> str:
    return contracts.normalize_answer(text, grading)


def _grade(item: dict, attempt: str) -> bool:
    """Server-authoritative grading, per exercise type (ADR-005/014)."""
    t = item["type"]
    if t == "word_sort":
        return _normalize(attempt, item["grading"]) == _normalize(
            item["payload"]["correct_bucket"], item["grading"]
        )
    if t == "bd_ninja":
        # client-scored game (ADR-014 §4): attempt = "hits/wrong", lenient pass.
        # Plausibility-checked: scores the round can't physically produce are
        # rejected (a forged "99/0" is not a win).
        try:
            hits, wrong = (int(x) for x in attempt.split("/", 1))
        except (ValueError, AttributeError):
            return False
        goal = item["payload"].get("goal", 1)
        max_wrong = len(item["payload"].get("letters", [])) - goal
        if hits < 0 or wrong < 0 or hits > goal or wrong > max(0, max_wrong):
            return False
        return hits >= max(1, round(goal * config.BD_NINJA_PASS)) and wrong <= 2
    return _normalize(attempt, item["grading"]) == _normalize(item["target"], item["grading"])


def _content(student_id: str, today: date):
    """The selector's content provider (ADR-014 §3) — the one source of what a
    skill's practicable material is, including the bankless skills."""
    skills_doc = store.load(student_id, "skills")
    return selector.make_content_provider(skills_doc, store.load_word_bank, today)


def _build_teach(focus_skill: str, content) -> dict:
    """The one mini-lesson card for the session's focus pattern (PLAN §7 step 3).
    The rule is generated from the FIRST example so it sounds out real content."""
    words = content(focus_skill)
    example = words[0] if words else {"word": focus_skill, "phonemes": []}
    rule_id, text = contracts.why_for(focus_skill, example)
    return {
        "skill_id": focus_skill,
        "rule_id": rule_id,
        "text": text,
        "examples": [w["word"] for w in words[:2]],
    }


def _public_state(state: dict, student_id: str) -> dict:
    """The session view sent to the client (no answer keys)."""
    cursor = state["cursor"]
    items = state["items"]
    item_view = contracts.public_item(items[cursor]["item"]) if cursor < len(items) else None
    slot = items[cursor].get("slot", "focus") if cursor < len(items) else None
    # Compute the teach card FRESH from the focus skill on every read (not from a
    # value baked into current.json at start), so content fixes apply immediately
    # even to a session already in progress.
    focus = state.get("focus_skill")
    teach = (
        _build_teach(focus, _content(student_id, date.fromisoformat(state["date"])))
        if focus
        else None
    )
    return {
        "session_id": state["session_id"],
        "focus_skill": state["focus_skill"],
        "teach": teach,
        "cursor": cursor,
        "slot": slot,
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
        return _public_state(existing, student_id)  # resume from cursor

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
                "slot": entry["slot"],
                "attempts": [],
                "stars": 0,
                "resolved": False,
                "misses": 0,
            }
        )

    # Focus = what the selector actually built the plan around.
    focus = next((e["skill_id"] for e in plan if e["slot"] == "focus"), None)
    if focus is None and plan:
        focus = plan[0]["skill_id"]
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
    return _public_state(state, student_id)


def get_item(student_id: str) -> dict | None:
    state = store.load_current_session(student_id)
    if not state:
        return None
    return _public_state(state, student_id)


def skip_item(student_id: str) -> dict:
    """Skip the CURRENT item without penalty — only allowed for the challenge slot
    (PLAN §7 step 5: 'skippable without penalty'). No mastery change, no stars
    lost, session just moves on."""
    state = store.load_current_session(student_id)
    if not state:
        return {"error": "no_active_session"}
    cursor = state["cursor"]
    if cursor >= len(state["items"]):
        return {"error": "session_complete"}
    if state["items"][cursor].get("slot") != "challenge":
        return {"error": "not_skippable"}
    state["items"][cursor]["resolved"] = True
    state["cursor"] += 1
    store.save_current_session(student_id, state)
    return {"skipped": True, "done": state["cursor"] >= len(state["items"])}


# --------------------------------------------------------------- answer
_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍﻿"))


def _sanitize_attempt(attempt) -> str | None:
    """Defensive input hygiene: only strings, control/zero-width chars stripped,
    length clamped (a 10k-char paste must not stall the Levenshtein aligner)."""
    if not isinstance(attempt, str):
        return None
    cleaned = attempt.translate(_ZERO_WIDTH)
    cleaned = "".join(ch for ch in cleaned if ch.isprintable())
    return cleaned[: config.MAX_ATTEMPT_LEN]


def submit_answer(
    student_id: str,
    item_id: str,
    attempt: str,
    phase: str = "first",  # kept for API compat; the REAL phase is server-derived
    today: date | None = None,
) -> dict:
    """Grade one answer server-side, classify a miss, update mastery, advance.

    HARDENED (owner mandate 2026-07-09) — every kid edge case gets a designed
    response, and the client is never trusted about game state:
    * the phase is DERIVED from stored attempts (a refresh after seeing the
      reveal can never earn first-try stars);
    * a blank answer never reveals the target (no free-answer cheat) — "stay";
    * resubmitting the identical wrong answer doesn't double-count misses
      (double-tap) — "stay" with a look-again nudge;
    * after the reveal she gets MAX_RETYPE_TRIES copying attempts with gentle
      nudges, then the session moves on warmly (never trapped, never punished).
    """
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

    attempt = _sanitize_attempt(attempt)
    if attempt is None:
        return {"error": "bad_attempt"}

    target = item["target"]
    grading = item["grading"]

    # blank answer → never reveal; gentle nudge, nothing counted
    if contracts.normalize_answer(attempt, grading) == "":
        return {
            "correct": False, "next": "stay", "nudge": "empty",
            "message": "Type your answer first 🙂 Tap 🔊 to hear it again!",
        }

    # the TRUE phase comes from the server's own record, never the client
    corrected = bool(entry["attempts"])

    # identical resubmit of the last wrong answer (double-tap, or nothing changed)
    if entry["attempts"]:
        last = entry["attempts"][-1]
        if contracts.normalize_answer(last["attempt"], grading) == contracts.normalize_answer(
            attempt, grading
        ):
            return {
                "correct": False, "next": "stay", "nudge": "same_again",
                "message": "That's the same as before — look really closely 👀",
            }

    correct = _grade(item, attempt)
    is_text = item["type"] in contracts.TEXT_TYPES
    if is_text or item["type"] == "bd_ninja":
        # multi-word / game answers aren't letter-aligned — tag coarsely
        result = {"tags": ["correct"] if correct else ["pattern_violation"]}
        result["primary"] = result["tags"][0]
    else:
        result = classifier.classify(
            attempt,
            target,
            is_heart_word=entry["skill_id"] == "heart_words",
            target_phonemes=entry["word"].get("phonemes"),
        )
    entry["attempts"].append(
        {
            "attempt": attempt,
            "phase": "retry" if corrected else "first",
            "correct": correct,
            "tags": result["tags"],
        }
    )

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
        if is_text:
            # phrase/sentence writing gets a REVIEW: praise-first, ≤2 corrections,
            # each with a why (the owner's core ask) — agent, or deterministic diff.
            why = teacher.review_writing(
                target, attempt, _review_fallback(target, attempt),
                memory_tail=store.read_memory(student_id)[-600:],
            )
        else:
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

    # wrong AGAIN while copying the revealed word → nudge, then move on warmly
    if not correct and corrected:
        entry["retype_tries"] = entry.get("retype_tries", 0) + 1
        if entry["retype_tries"] < config.MAX_RETYPE_TRIES:
            store.save_current_session(student_id, state)
            return {
                "correct": False, "next": "stay", "nudge": "copy_again",
                "message": "Almost! Look at each letter and copy it once more 💪",
            }
        # enough — never trap the child on one word (PLAN §1)
        _apply_mastery(student_id, entry["skill_id"], score, day)
        entry["stars"] = 0
        entry["resolved"] = True
        state["cursor"] += 1
        store.save_current_session(student_id, state)
        return {
            "correct": False, "stars": 0, "tags": result["tags"],
            "next": "advance", "nudge": "move_on",
            "message": "We'll practice that one again another day 💛",
            "done": state["cursor"] >= len(state["items"]),
            "totals": state["totals"],
        }

    # resolved correctly (first try, or the retype): score mastery + advance
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


def _review_fallback(target: str, attempt: str) -> str:
    """Deterministic writing review (ADR-014 §5): praise first, then at most TWO
    corrections, each with a sound-out why — never a wall of red ink (PLAN §1)."""
    grading = {"case_insensitive": True, "trim": True, "ignore_punctuation": True, "collapse_spaces": True}
    t_words = contracts.normalize_answer(target, grading).split()
    a_words = contracts.normalize_answer(attempt, grading).split()
    fixes: list[str] = []
    for i, tw in enumerate(t_words):
        aw = a_words[i] if i < len(a_words) else None
        if aw != tw:
            sounds = " ".join(f"/{g}/" for g in phonics.segment_graphemes(tw))
            fixes.append(f"“{tw}” — sound it out: {sounds}")
            if len(fixes) == 2:
                break
    if not fixes:
        return f"So close! Listen once more and write it word by word: {target}"
    n = "one word" if len(fixes) == 1 else "two words"
    return f"Great writing! Let's polish {n}: " + "; ".join(fixes) + "."


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
        # only real word items step down (a phrase/sentence/game can't become tiles)
        if not entry["word"].get("kind"):
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
    # bank the session's earned stars (drives xp/levels — invariant #3 add-only)
    rewards.add_stars(rewards_doc, state["totals"]["stars"])
    hatched = rewards.hatch_creatures(rewards_doc, skills_doc, previous, day)
    # the streak counts only for a REAL session (≥ half the items actually done) —
    # finishing instantly to farm the flame doesn't work; stars stay as earned
    resolved = sum(1 for e in state["items"] if e.get("resolved"))
    did_enough = resolved >= max(1, int(len(state["items"]) * config.MIN_RESOLVED_FRACTION))
    rewards.apply_session_end(rewards_doc, skills_doc, previous, day, count_streak=did_enough)
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
