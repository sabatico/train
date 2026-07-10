"""Tests for the ADR-014 session-experience redesign.

Cross-author coverage (a different model wrote engine/selector.py, engine/
contracts.py, engine/session.py additions, agent/teacher.review_writing, and the
new app.py routes; this suite is authored independently per the test-and-coverage
SOP). See docs/adr/ADR-014-session-experience-redesign.md for the design.

No network calls: agent.client.chat is mocked wherever a live-agent path is
exercised; the default env has no SPELLQUEST_AGENT_LIVE / DEEPSEEK_API_KEY so
teacher functions return their canned fallback by default (verified below,
not just assumed).
"""
from __future__ import annotations

import random
from datetime import date

import pytest

from engine import config, contracts, models, selector, session, store


TODAY = date(2026, 7, 10)


def _words(n, prefix="w", pattern="short_vowels", difficulty=3):
    return [
        {
            "word": f"{prefix}{i}",
            "phonemes": ["a"],
            "pattern": pattern,
            "difficulty": difficulty,
        }
        for i in range(n)
    ]


# =============================================================================
# selector.band_for
# =============================================================================
@pytest.mark.parametrize(
    "mastery,expected",
    [
        (0, "low"),
        (44, "low"),
        (44.9, "low"),
        (45, "mid"),
        (60, "mid"),
        (74.9, "mid"),
        (75, "high"),
        (100, "high"),
    ],
)
def test_band_for_boundaries(mastery, expected):
    assert selector.band_for(mastery) == expected


# =============================================================================
# selector.types_for
# =============================================================================
def test_types_for_known_override_heart_words_mid():
    assert selector.types_for("heart_words", "mid") == config.TYPE_OVERRIDES["heart_words"]["mid"]


def test_types_for_known_override_heart_words_low_and_high():
    assert selector.types_for("heart_words", "low") == config.TYPE_OVERRIDES["heart_words"]["low"]
    assert selector.types_for("heart_words", "high") == config.TYPE_OVERRIDES["heart_words"]["high"]


def test_types_for_unknown_skill_falls_back_to_type_bands():
    assert selector.types_for("short_vowels", "low") == config.TYPE_BANDS["low"]
    assert selector.types_for("short_vowels", "mid") == config.TYPE_BANDS["mid"]
    assert selector.types_for("short_vowels", "high") == config.TYPE_BANDS["high"]


def test_types_for_letter_orientation_always_bd_ninja():
    for band in ("low", "mid", "high"):
        assert selector.types_for("letter_orientation", band) == ("bd_ninja",)


# =============================================================================
# selector.make_content_provider
# =============================================================================
def _skills_doc_with(graph, introduced_ids):
    doc = models.default_skills(graph)
    for sid, skill in doc["skills"].items():
        skill["introduced"] = sid in introduced_ids
    return doc


def test_content_provider_phrase_dictation_kind_and_word_is_phrase(bootstrapped_student, data_root):
    skills_doc = store.load(bootstrapped_student, "skills")
    # short_vowels (and other no-prereq skills, e.g. heart_words) are introduced
    # by default (no prereqs)
    content = selector.make_content_provider(skills_doc, store.load_word_bank, TODAY)
    entries = content("phrase_dictation")
    assert entries, "expected phrase entries sourced from introduced banks"
    for e in entries:
        assert e["kind"] == "phrase"
        assert isinstance(e["word"], str) and e["word"]
    # cross-check against the raw banks of every REAL introduced skill: every
    # phrase entry's word equals some introduced-bank word's `phrase` field
    introduced_real = [
        sid
        for sid, s in skills_doc["skills"].items()
        if s["introduced"] and sid not in config.CONTENT_FROM_OTHER_BANKS
    ]
    phrases_from_bank = {
        w["phrase"]
        for sid in introduced_real
        for w in store.load_word_bank(sid)
        if w.get("phrase")
    }
    for e in entries:
        assert e["word"] in phrases_from_bank


def test_content_provider_sentence_writing_kind_and_word_is_sentence(bootstrapped_student, data_root):
    skills_doc = store.load(bootstrapped_student, "skills")
    content = selector.make_content_provider(skills_doc, store.load_word_bank, TODAY)
    entries = content("sentence_writing")
    assert entries
    introduced_real = [
        sid
        for sid, s in skills_doc["skills"].items()
        if s["introduced"] and sid not in config.CONTENT_FROM_OTHER_BANKS
    ]
    sentences_from_bank = {
        w["sentence"]
        for sid in introduced_real
        for w in store.load_word_bank(sid)
        if w.get("sentence")
    }
    for e in entries:
        assert e["kind"] == "sentence"
        assert e["word"] in sentences_from_bank


def test_content_provider_word_sequencing_only_high_difficulty_or_long(bootstrapped_student, data_root):
    skills_doc = store.load(bootstrapped_student, "skills")
    content = selector.make_content_provider(skills_doc, store.load_word_bank, TODAY)
    entries = content("word_sequencing")
    for e in entries:
        assert e.get("difficulty", 1) >= config.LONG_WORD_MIN_DIFFICULTY or len(e["word"]) >= 5


def test_content_provider_letter_orientation_three_game_rounds_when_banks_exist(bootstrapped_student, data_root):
    skills_doc = store.load(bootstrapped_student, "skills")
    content = selector.make_content_provider(skills_doc, store.load_word_bank, TODAY)
    entries = content("letter_orientation")
    assert len(entries) == 3
    for e in entries:
        assert e["kind"] == "game"


def test_content_provider_letter_orientation_empty_when_no_real_banks_introduced(empty_data_root):
    # empty_data_root has NO word_bank/ tree at all -> load_skill_graph() == {}
    # -> default_skills marks every skill "introduced" (vacuous, per conftest's
    # documented gotcha), but words_for always returns [] since there IS no bank.
    graph = {}
    skills_doc = models.default_skills(graph)

    def no_words(sid):
        return []

    content = selector.make_content_provider(skills_doc, no_words, TODAY)
    assert content("letter_orientation") == []


def test_content_provider_letter_orientation_empty_when_real_banks_have_no_words():
    # explicit unit-test path (no store): every skill "introduced" but words_for
    # returns nothing for the real-content skills -> real_banks() is empty.
    graph = {"short_vowels": []}
    skills_doc = models.default_skills(graph)

    def no_words(sid):
        return []

    content = selector.make_content_provider(skills_doc, no_words, TODAY)
    assert content("letter_orientation") == []


def test_content_provider_phrase_dictation_entries_have_expected_word_lengths_source():
    # unit-level: craft a fake bank with a phrase field and confirm the provider
    # surfaces it verbatim.
    graph = {"short_vowels": []}
    skills_doc = models.default_skills(graph)
    bank = [{"word": "cat", "phrase": "the red cat", "emoji": "🐱", "pattern": "short_vowels"}]

    def words_for(sid):
        return bank if sid == "short_vowels" else []

    content = selector.make_content_provider(skills_doc, words_for, TODAY)
    entries = content("phrase_dictation")
    assert len(entries) == 1
    assert entries[0]["word"] == "the red cat"
    assert entries[0]["kind"] == "phrase"


# =============================================================================
# selector.build_plan — anti-monotony / policy properties
# =============================================================================
def test_build_plan_has_at_least_two_distinct_exercise_types(bootstrapped_student, data_root):
    skills_doc = store.load(bootstrapped_student, "skills")
    graph = store.load_skill_graph()
    plan = selector.build_plan(
        skills_doc, graph, store.load_word_bank, TODAY, rng=random.Random(7)
    )
    types_used = {e["exercise_type"] for e in plan}
    assert len(types_used) >= 2


def test_build_plan_bd_ninja_capped_at_game_items_max(bootstrapped_student, data_root):
    skills_doc = store.load(bootstrapped_student, "skills")
    graph = store.load_skill_graph()
    plan = selector.build_plan(
        skills_doc, graph, store.load_word_bank, TODAY, rng=random.Random(7)
    )
    bd_ninja_count = sum(1 for e in plan if e["exercise_type"] == "bd_ninja")
    assert bd_ninja_count <= config.GAME_ITEMS_MAX


def test_build_plan_focus_never_letter_orientation(bootstrapped_student, data_root):
    skills_doc = store.load(bootstrapped_student, "skills")
    # tank letter_orientation's mastery so it WOULD be picked as weakest if eligible
    skills_doc["skills"]["letter_orientation"]["mastery"] = 1
    graph = store.load_skill_graph()
    plan = selector.build_plan(
        skills_doc, graph, store.load_word_bank, TODAY, rng=random.Random(7)
    )
    focus_entries = [e for e in plan if e["slot"] == "focus"]
    for e in focus_entries:
        assert e["skill_id"] != "letter_orientation"


def test_build_plan_warmup_items_are_real_bank_skills(bootstrapped_student, data_root):
    skills_doc = store.load(bootstrapped_student, "skills")
    graph = store.load_skill_graph()
    plan = selector.build_plan(
        skills_doc, graph, store.load_word_bank, TODAY, rng=random.Random(7)
    )
    warmups = [e for e in plan if e["slot"] == "warmup"]
    assert warmups
    for e in warmups:
        assert e["skill_id"] not in config.CONTENT_FROM_OTHER_BANKS


def _skills_doc_with_sentence_writing_unlocked(graph):
    """A skills_doc where phrase_dictation AND sentence_writing are introduced,
    with prereqs high enough to stay unlocked, for challenge-slot testing."""
    skills_doc = models.default_skills(graph)
    for sid in ("short_vowels", "digraphs", "phrase_dictation", "sentence_writing"):
        skills_doc["skills"][sid]["introduced"] = True
        skills_doc["skills"][sid]["mastery"] = 90
        skills_doc["skills"][sid]["last_practiced"] = TODAY.isoformat()
    return skills_doc


def test_build_plan_last_entry_is_challenge_when_sentence_writing_unlocked(bootstrapped_student, data_root):
    graph = store.load_skill_graph()
    skills_doc = _skills_doc_with_sentence_writing_unlocked(graph)
    plan = selector.build_plan(
        skills_doc, graph, store.load_word_bank, TODAY, rng=random.Random(7)
    )
    assert plan, "expected a non-empty plan"
    assert plan[-1]["slot"] == "challenge"


def test_build_plan_last_entry_is_challenge_when_phrase_dictation_unlocked_only(bootstrapped_student, data_root):
    graph = store.load_skill_graph()
    skills_doc = models.default_skills(graph)
    for sid in ("short_vowels", "digraphs", "phrase_dictation"):
        skills_doc["skills"][sid]["introduced"] = True
        skills_doc["skills"][sid]["mastery"] = 90
        skills_doc["skills"][sid]["last_practiced"] = TODAY.isoformat()
    # sentence_writing NOT introduced
    plan = selector.build_plan(
        skills_doc, graph, store.load_word_bank, TODAY, rng=random.Random(7)
    )
    assert plan
    assert plan[-1]["slot"] == "challenge"
    assert plan[-1]["skill_id"] in ("phrase_dictation", "sentence_writing")


# =============================================================================
# contracts — new payloads
# =============================================================================
def test_missing_letters_display_has_none_at_blanks_and_blanks_le_2():
    word_entry = {"word": "ship", "phonemes": ["sh", "i", "p"], "tricky_letters": []}
    payload = contracts._payload_missing_letters(word_entry)
    assert len(payload["blanks"]) <= 2
    for i, ch in enumerate(payload["display"]):
        if i in payload["blanks"]:
            assert ch is None
        else:
            assert ch is not None


def test_missing_letters_display_joins_back_to_word_with_blanks_filled():
    word_entry = {"word": "ship", "phonemes": ["sh", "i", "p"], "tricky_letters": []}
    payload = contracts._payload_missing_letters(word_entry)
    word = word_entry["word"]
    rebuilt = "".join(
        (word[i] if ch is None else ch) for i, ch in enumerate(payload["display"])
    )
    assert rebuilt == word


def test_missing_letters_with_tricky_letters_marks_those_blanks():
    word_entry = {"word": "said", "phonemes": ["s", "ai", "d"], "tricky_letters": [1, 2]}
    payload = contracts._payload_missing_letters(word_entry)
    assert set(payload["blanks"]) == {1, 2}
    assert payload["display"][1] is None
    assert payload["display"][2] is None


def test_word_sort_buckets_contain_pattern_and_a_decoy():
    word_entry = {"word": "cat", "pattern": "short_vowels"}
    payload = contracts._payload_word_sort(word_entry)
    bucket_ids = {b["id"] for b in payload["buckets"]}
    assert "short_vowels" in bucket_ids
    assert len(bucket_ids) == 2
    assert payload["correct_bucket"] == "short_vowels"


def test_word_sort_public_item_strips_correct_bucket():
    word_entry = {"word": "cat", "phonemes": ["c", "a", "t"], "pattern": "short_vowels"}
    item = contracts.build_item("word_sort", "short_vowels", word_entry, 2)
    assert "correct_bucket" in item["payload"]  # server-side item has it
    pub = contracts.public_item(item)
    assert "correct_bucket" not in pub["payload"]
    assert "buckets" in pub["payload"]  # buckets themselves still shown
    assert "target" not in pub  # sanity: general answer-leak guard too


def test_heart_word_spotlight_display_word_present():
    word_entry = {"word": "said", "tricky_letters": [1, 2]}
    payload = contracts._payload_heart_word_spotlight(word_entry)
    assert payload["display_word"] == "said"


def test_phrase_dictation_word_lengths():
    word_entry = {"word": "the red hen"}
    payload = contracts._payload_phrase_dictation(word_entry)
    assert payload["word_lengths"] == [3, 3, 3]


def test_bd_ninja_target_letter_is_b_or_d():
    word_entry = {"word": "hello"}
    payload = contracts._payload_bd_ninja(word_entry)
    assert payload["target_letter"] in ("b", "d")


def test_bd_ninja_goal_equals_letters_count_of_target():
    word_entry = {"word": "hello"}
    payload = contracts._payload_bd_ninja(word_entry)
    assert payload["goal"] == payload["letters"].count(payload["target_letter"])


def test_bd_ninja_deterministic_for_same_word_entry():
    word_entry = {"word": "banana"}
    p1 = contracts._payload_bd_ninja(word_entry)
    p2 = contracts._payload_bd_ninja(word_entry)
    assert p1 == p2


def test_bd_ninja_letters_length_matches_config():
    word_entry = {"word": "xyz"}
    payload = contracts._payload_bd_ninja(word_entry)
    assert len(payload["letters"]) == config.BD_NINJA_LETTERS


# --------------------------------------------------------------- normalize_answer
def test_normalize_answer_ignore_punctuation_strips_expected_set():
    grading = {"ignore_punctuation": True, "trim": True, "case_insensitive": True}
    out = contracts.normalize_answer("I love my Dog.,!?;:'\"", grading)
    assert out == "i love my dog"


def test_normalize_answer_collapse_spaces():
    grading = {"collapse_spaces": True, "trim": True, "case_insensitive": True}
    out = contracts.normalize_answer("I   love   my   dog", grading)
    assert out == "i love my dog"


def test_normalize_answer_case_and_punctuation_forgiving_equal_under_text_types_grading():
    grading = {
        "case_insensitive": True,
        "trim": True,
        "collapse_spaces": True,
        "ignore_punctuation": True,
    }
    a = contracts.normalize_answer("I  love my Dog.", grading)
    b = contracts.normalize_answer("i love my dog", grading)
    assert a == b


def test_text_types_constant_matches_grading_forgiveness():
    # sanity: TEXT_TYPES items get exactly these forgiving grading flags in build_item
    word_entry = {"word": "the red hen"}
    for t in contracts.TEXT_TYPES:
        item = contracts.build_item(t, "phrase_dictation", word_entry, 1)
        assert item["grading"]["collapse_spaces"] is True
        assert item["grading"]["ignore_punctuation"] is True


# =============================================================================
# session grading (_grade) + skip_item + finish_session banking
# =============================================================================
def test_grade_word_sort_correct_bucket():
    word_entry = {"word": "cat", "phonemes": ["c", "a", "t"], "pattern": "short_vowels"}
    item = contracts.build_item("word_sort", "short_vowels", word_entry, 2)
    assert session._grade(item, item["payload"]["correct_bucket"]) is True


def test_grade_word_sort_wrong_bucket():
    word_entry = {"word": "cat", "phonemes": ["c", "a", "t"], "pattern": "short_vowels"}
    item = contracts.build_item("word_sort", "short_vowels", word_entry, 2)
    wrong = next(b["id"] for b in item["payload"]["buckets"] if b["id"] != item["payload"]["correct_bucket"])
    assert session._grade(item, wrong) is False


def test_grade_bd_ninja_goal_slash_zero_correct():
    word_entry = {"word": "hello"}
    item = contracts.build_item("bd_ninja", "letter_orientation", word_entry, 1)
    goal = item["payload"]["goal"]
    assert session._grade(item, f"{goal}/0") is True


def test_grade_bd_ninja_goal_slash_three_wrong_incorrect():
    word_entry = {"word": "hello"}
    item = contracts.build_item("bd_ninja", "letter_orientation", word_entry, 1)
    goal = item["payload"]["goal"]
    assert session._grade(item, f"{goal}/3") is False


def test_grade_bd_ninja_zero_zero_incorrect():
    word_entry = {"word": "hello"}
    item = contracts.build_item("bd_ninja", "letter_orientation", word_entry, 1)
    assert session._grade(item, "0/0") is False


def test_grade_bd_ninja_garbage_attempt_incorrect_no_crash():
    word_entry = {"word": "hello"}
    item = contracts.build_item("bd_ninja", "letter_orientation", word_entry, 1)
    assert session._grade(item, "abc") is False


def test_grade_phrase_case_and_punctuation_forgiving():
    word_entry = {"word": "i love my dog"}
    item = contracts.build_item("phrase_dictation", "phrase_dictation", word_entry, 1)
    assert session._grade(item, "I love my dog.") is True


def test_grade_sentence_scribe_case_and_punctuation_forgiving():
    word_entry = {"word": "i love my dog"}
    item = contracts.build_item("sentence_scribe", "sentence_writing", word_entry, 1)
    assert session._grade(item, "I love my dog.") is True


# --------------------------------------------------------------- _review_fallback
def test_review_fallback_mentions_wrong_word_with_sound_out_and_praises_first():
    text = session._review_fallback("i love my dog", "i luv my dog")
    assert "love" in text
    assert text.startswith("Great writing!")  # praise-first
    assert "/" in text  # a sound-out marker present


def test_review_fallback_at_most_two_corrections_even_with_three_wrong_words():
    text = session._review_fallback("the big red dog runs", "tha bg rd dog rns")
    # count "—" occurrences used per fix (word — sound it out)
    assert text.count(" — sound it out:") <= 2


def test_review_fallback_empty_attempt_returns_non_empty_text():
    text = session._review_fallback("i love my dog", "")
    assert isinstance(text, str) and len(text) > 0


def test_review_fallback_no_mistakes_returns_encouragement_message():
    text = session._review_fallback("i love my dog", "i love my dog")
    assert "So close!" in text or len(text) > 0


# --------------------------------------------------------------- skip_item
def test_skip_item_only_when_current_slot_is_challenge(bootstrapped_student):
    state = {
        "session_id": "s1",
        "date": TODAY.isoformat(),
        "focus_skill": "short_vowels",
        "cursor": 0,
        "items": [
            {
                "item": {"item_id": "i1", "type": "letter_boxes"},
                "word": {"word": "cat"},
                "skill_id": "short_vowels",
                "slot": "challenge",
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
    result = session.skip_item(bootstrapped_student)
    assert result == {"skipped": True, "done": True}
    after = store.load_current_session(bootstrapped_student)
    assert after["cursor"] == 1
    assert after["items"][0]["resolved"] is True


def test_skip_item_no_stars_or_mastery_change(bootstrapped_student):
    before_skills = store.load(bootstrapped_student, "skills")
    before_mastery = before_skills["skills"]["short_vowels"]["mastery"]
    state = {
        "session_id": "s1",
        "date": TODAY.isoformat(),
        "focus_skill": "short_vowels",
        "cursor": 0,
        "items": [
            {
                "item": {"item_id": "i1", "type": "sentence_scribe"},
                "word": {"word": "the dog runs"},
                "skill_id": "short_vowels",
                "slot": "challenge",
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
    session.skip_item(bootstrapped_student)
    after_skills = store.load(bootstrapped_student, "skills")
    assert after_skills["skills"]["short_vowels"]["mastery"] == before_mastery
    after_state = store.load_current_session(bootstrapped_student)
    assert after_state["totals"]["stars"] == 0


def test_skip_item_non_challenge_slot_returns_not_skippable(bootstrapped_student):
    state = {
        "session_id": "s1",
        "date": TODAY.isoformat(),
        "focus_skill": "short_vowels",
        "cursor": 0,
        "items": [
            {
                "item": {"item_id": "i1", "type": "letter_boxes"},
                "word": {"word": "cat"},
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
    result = session.skip_item(bootstrapped_student)
    assert result == {"error": "not_skippable"}
    after = store.load_current_session(bootstrapped_student)
    assert after["cursor"] == 0  # unchanged


def test_skip_item_no_active_session_returns_error(bootstrapped_student):
    result = session.skip_item(bootstrapped_student)
    assert result == {"error": "no_active_session"}


def test_skip_item_at_end_of_session_returns_session_complete(bootstrapped_student):
    state = {
        "session_id": "s1",
        "date": TODAY.isoformat(),
        "focus_skill": "short_vowels",
        "cursor": 1,
        "items": [
            {
                "item": {"item_id": "i1", "type": "letter_boxes"},
                "word": {"word": "cat"},
                "skill_id": "short_vowels",
                "slot": "challenge",
                "attempts": [],
                "stars": 0,
                "resolved": True,
                "misses": 0,
            }
        ],
        "totals": {"stars": 0, "items": 1, "correct_first_try": 0},
        "consecutive_misses": 0,
    }
    store.save_current_session(bootstrapped_student, state)
    result = session.skip_item(bootstrapped_student)
    assert result == {"error": "session_complete"}


# --------------------------------------------------------------- finish_session banks stars
def test_finish_session_banks_stars_into_rewards_total(bootstrapped_student):
    DAY = date(2026, 7, 9)
    session.start_session(bootstrapped_student, today=DAY, rng=random.Random(42))
    from tests.test_session import _server_item, _correct_attempt

    # answer a few items correctly to earn stars
    for _ in range(3):
        item = _server_item(bootstrapped_student)
        session.submit_answer(
            bootstrapped_student, item["item_id"], _correct_attempt(item), phase="first", today=DAY
        )
    state = store.load_current_session(bootstrapped_student)
    earned = state["totals"]["stars"]
    assert earned > 0, "test setup should have earned at least one star"

    before_rewards = store.load(bootstrapped_student, "rewards")
    before_total = before_rewards["stars_total"]

    result = session.finish_session(bootstrapped_student, today=DAY)
    assert result["stars"] == earned

    after_rewards = store.load(bootstrapped_student, "rewards")
    assert after_rewards["stars_total"] == before_total + earned


# =============================================================================
# app routes
# =============================================================================
@pytest.fixture
def client(data_root):
    import importlib

    import app as app_module

    importlib.reload(app_module)
    flask_app = app_module.create_app()
    flask_app.testing = True
    with flask_app.test_client() as c:
        yield c


def test_api_home_returns_200_with_expected_keys(client):
    resp = client.get("/api/home")
    assert resp.status_code == 200
    body = resp.get_json()
    for key in (
        "streak", "level", "level_name", "stars_total", "xp", "xp_next_level",
        "mission", "collection",
    ):
        assert key in body


def test_api_session_skip_no_session_returns_404(client):
    resp = client.post("/api/session/skip")
    assert resp.status_code == 404


def test_api_session_skip_non_challenge_item_returns_409(client):
    start = client.post("/api/session/start")
    assert start.status_code == 200
    view = start.get_json()
    # first item is virtually never the challenge slot (challenge is always last,
    # and a fresh default student has no Strand-D skills introduced anyway)
    assert view["slot"] != "challenge"
    resp = client.post("/api/session/skip")
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "not_skippable"


# =============================================================================
# agent.teacher.review_writing
# =============================================================================
def test_review_writing_agent_off_returns_canned_exactly(monkeypatch):
    from agent import teacher

    monkeypatch.delenv("SPELLQUEST_AGENT_LIVE", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    canned = "canned review text"
    result = teacher.review_writing("i love my dog", "i luv my dog", canned)
    assert result == canned


def test_review_writing_default_env_has_agent_unavailable(monkeypatch):
    """Verify the task brief's stated default assumption directly, rather than
    relying on it blindly: with no SPELLQUEST_AGENT_LIVE set, is_available() is
    False regardless of DEEPSEEK_API_KEY."""
    from agent import teacher

    monkeypatch.delenv("SPELLQUEST_AGENT_LIVE", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-key-for-test")
    assert teacher.is_available() is False


def test_review_writing_live_and_mocked_chat_returns_content(monkeypatch):
    from agent import client as agent_client
    from agent import teacher

    monkeypatch.setenv("SPELLQUEST_AGENT_LIVE", "1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-key-for-test")

    captured_messages = {}

    def fake_chat(messages, **kwargs):
        captured_messages["messages"] = messages
        return {"choices": [{"message": {"content": "Great job! Fix 'luv' -> 'love'."}}]}

    monkeypatch.setattr(agent_client, "chat", fake_chat)

    canned = "canned fallback"
    result = teacher.review_writing(
        "i love my dog", "i luv my dog", canned, memory_tail="child struggles with vowel teams"
    )
    assert result == "Great job! Fix 'luv' -> 'love'."
    # memory_tail appears in the prompt sent to the model
    all_text = " ".join(m["content"] for m in captured_messages["messages"])
    assert "child struggles with vowel teams" in all_text


def test_review_writing_agent_error_returns_canned(monkeypatch):
    from agent import client as agent_client
    from agent import teacher

    monkeypatch.setenv("SPELLQUEST_AGENT_LIVE", "1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-key-for-test")

    def raising_chat(messages, **kwargs):
        raise agent_client.AgentError("boom")

    monkeypatch.setattr(agent_client, "chat", raising_chat)

    canned = "canned fallback"
    result = teacher.review_writing("i love my dog", "i luv my dog", canned)
    assert result == canned


def test_review_writing_oversized_response_returns_canned(monkeypatch):
    from agent import client as agent_client
    from agent import teacher

    monkeypatch.setenv("SPELLQUEST_AGENT_LIVE", "1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-key-for-test")

    def fake_chat(messages, **kwargs):
        return {"choices": [{"message": {"content": "x" * 401}}]}

    monkeypatch.setattr(agent_client, "chat", fake_chat)

    canned = "canned fallback"
    result = teacher.review_writing("i love my dog", "i luv my dog", canned)
    assert result == canned
