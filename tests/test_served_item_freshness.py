"""Tests for the "served item is rebuilt fresh, never stale" fix in
`engine/session.py` (`_fresh_word` / `_served_item` / `_public_state`).

REGRESSION CONTEXT (owner-found, 3rd occurrence of the "stale baked content"
bug class): items are written into `sessions/current.json` once, at plan build
time. Before this fix, everything the child SAW (emoji, prompt text, tiles,
phoneme groups) was whatever was baked in at that moment — so a content fix
(e.g. correcting a wrong emoji or bad tile set in the word bank) never reached
a session already in progress. The fix keeps IDENTITY + GRADING AUTHORITY on
the stored item (`item_id`, `target`, answer keys like `correct_bucket`) but
rebuilds everything the child sees from the CURRENT word bank on every read
(`get_item` / `start_session` resume / mid-session state via `_public_state`).

Synthetic content (word.kind in phrase/sentence/game) has no bank row to look
up, so it keeps its stored form unchanged (no crash, no lookup).

All time-dependent calls use an explicit `today`; `start_session` also takes a
seeded `rng` (see tests/test_session.py conventions).
"""
from __future__ import annotations

import random
from datetime import date

from engine import contracts, session, store

DAY = date(2026, 7, 7)
SEED = 42


def _current(student_id):
    return store.load_current_session(student_id)


def _save(student_id, state):
    store.save_current_session(student_id, state)


# --------------------------------------------------------------- regression: emoji freshness
def test_served_emoji_ignores_stale_baked_value(bootstrapped_student):
    """The owner's bug, 3rd occurrence: corrupt the STORED emoji on both the
    item's prompt and the entry's word dict; the served item must show the
    CURRENT bank's emoji for that word, not the stale/corrupted one."""
    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    state = _current(bootstrapped_student)
    entry = state["items"][state["cursor"]]

    word = entry["word"]
    assert not word.get("kind"), "regression test needs a real bank word, not synthetic content"
    truth = next(
        w for w in store.load_word_bank(word["pattern"]) if w["word"] == word["word"]
    )

    # corrupt BOTH places the stale bug could have leaked the baked value from
    entry["item"]["prompt"]["image_emoji"] = "👋"
    entry["word"]["emoji"] = "👋"
    _save(bootstrapped_student, state)

    view = session.get_item(bootstrapped_student)
    served_emoji = view["item"]["prompt"]["image_emoji"]
    assert served_emoji == truth.get("emoji", "")
    assert served_emoji != "👋"


# --------------------------------------------------------------- tiles freshness
def test_served_word_builder_tiles_ignore_stale_corrupted_payload(bootstrapped_student):
    """Corrupt a word_builder item's stored tiles to nonsense; the SERVED payload
    must have correct tiles again — joining the correct (non-distractor) tiles
    must spell the target."""
    words = store.load_word_bank("short_vowels")
    bag = next(w for w in words if w["word"] == "bag")
    item = contracts.build_item("word_builder", "short_vowels", bag, 1)

    state = {
        "session_id": "sess-1",
        "date": DAY.isoformat(),
        "focus_skill": "short_vowels",
        "cursor": 0,
        "items": [
            {
                "item": item,
                "word": bag,
                "skill_id": "short_vowels",
                "slot": "focus",
                "attempts": [],
                "stars": 0,
                "resolved": False,
                "misses": 0,
            }
        ],
        "totals": {"stars": 0, "items": 1, "correct_first_try": 0},
        "consecutive_misses": 0,
    }
    store.save_current_session(bootstrapped_student, state)

    # corrupt the stored payload's tiles
    corrupted = _current(bootstrapped_student)
    corrupted["items"][0]["item"]["payload"]["tiles"] = ["x", "y"]
    _save(bootstrapped_student, corrupted)

    view = session.get_item(bootstrapped_student)
    tiles = view["item"]["payload"]["tiles"]
    assert tiles != ["x", "y"]
    # the correct (spellable) tiles are a prefix matching the sound_boxes count;
    # joining exactly that many tiles must spell the target
    n_boxes = len(view["item"]["payload"]["sound_boxes"])
    assert "".join(tiles[:n_boxes]).lower() == "bag"


# --------------------------------------------------------------- item_id + hidden target + grading
def test_served_item_keeps_stored_item_id_hides_target_and_grades_on_stored_target(
    bootstrapped_student,
):
    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(SEED))
    state = _current(bootstrapped_student)
    entry = state["items"][state["cursor"]]
    stored_item_id = entry["item"]["item_id"]
    stored_target = entry["item"]["target"]

    # corrupt served-content fields to make sure they don't affect identity/grading
    word = entry["word"]
    if not word.get("kind"):
        word["emoji"] = "👋"
    _save(bootstrapped_student, state)

    view = session.get_item(bootstrapped_student)
    assert view["item"]["item_id"] == stored_item_id
    assert "target" not in view["item"]

    result = session.submit_answer(
        bootstrapped_student, stored_item_id, stored_target, phase="first", today=DAY
    )
    assert result["correct"] is True


# --------------------------------------------------------------- word_sort answer key stripped
def test_served_word_sort_correct_bucket_stripped_after_rebuild(bootstrapped_student):
    words = store.load_word_bank("short_vowels")
    bag = next(w for w in words if w["word"] == "bag")
    item = contracts.build_item("word_sort", "short_vowels", bag, 1)
    assert "correct_bucket" in item["payload"]  # sanity: the server copy HAS the key

    state = {
        "session_id": "sess-2",
        "date": DAY.isoformat(),
        "focus_skill": "short_vowels",
        "cursor": 0,
        "items": [
            {
                "item": item,
                "word": bag,
                "skill_id": "short_vowels",
                "slot": "focus",
                "attempts": [],
                "stars": 0,
                "resolved": False,
                "misses": 0,
            }
        ],
        "totals": {"stars": 0, "items": 1, "correct_first_try": 0},
        "consecutive_misses": 0,
    }
    store.save_current_session(bootstrapped_student, state)

    view = session.get_item(bootstrapped_student)
    assert "correct_bucket" not in view["item"]["payload"]
    assert view["item"]["payload"]["chip"] == "bag"


# --------------------------------------------------------------- synthetic content (no bank lookup)
def test_served_synthetic_phrase_item_unchanged_no_bank_lookup_crash(bootstrapped_student):
    """A word with kind:'phrase' has no bank row — must serve unchanged, no crash."""
    synthetic_word = {"word": "the red hen", "kind": "phrase", "emoji": "🐔"}
    item = contracts.build_item(
        "phrase_dictation", "phrase_dictation", synthetic_word, 2
    )

    state = {
        "session_id": "sess-3",
        "date": DAY.isoformat(),
        "focus_skill": "phrase_dictation",
        "cursor": 0,
        "items": [
            {
                "item": item,
                "word": synthetic_word,
                "skill_id": "phrase_dictation",
                "slot": "focus",
                "attempts": [],
                "stars": 0,
                "resolved": False,
                "misses": 0,
            }
        ],
        "totals": {"stars": 0, "items": 1, "correct_first_try": 0},
        "consecutive_misses": 0,
    }
    store.save_current_session(bootstrapped_student, state)

    view = session.get_item(bootstrapped_student)
    assert view["item"]["prompt"]["image_emoji"] == "🐔"
    assert view["item"]["payload"]["word_lengths"] == [3, 3, 3]


# --------------------------------------------------------------- word not in its pattern's bank
def test_served_word_not_in_pattern_bank_serves_stored_form_without_crash(
    bootstrapped_student,
):
    """A word entry whose word isn't present in its pattern's bank (bank lookup
    misses entirely) must serve the stored form, not crash."""
    ghost_word = {
        "word": "ghostword",
        "phonemes": ["g", "h", "o", "s", "t", "w", "o", "r", "d"],
        "pattern": "nonexistent",
        "emoji": "👻",
        "tricky_letters": [],
    }
    item = contracts.build_item("letter_boxes", "short_vowels", ghost_word, 1)

    state = {
        "session_id": "sess-4",
        "date": DAY.isoformat(),
        "focus_skill": "short_vowels",
        "cursor": 0,
        "items": [
            {
                "item": item,
                "word": ghost_word,
                "skill_id": "short_vowels",
                "slot": "focus",
                "attempts": [],
                "stars": 0,
                "resolved": False,
                "misses": 0,
            }
        ],
        "totals": {"stars": 0, "items": 1, "correct_first_try": 0},
        "consecutive_misses": 0,
    }
    store.save_current_session(bootstrapped_student, state)

    view = session.get_item(bootstrapped_student)  # must not raise
    assert view["item"]["prompt"]["image_emoji"] == "👻"
    assert len(view["item"]["payload"]["boxes"]) == len("ghostword")
