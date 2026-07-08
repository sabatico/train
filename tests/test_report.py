"""Tests for engine/report.py — parent dashboard data + rose-of-winds radar geometry.

Pure functions over in-memory skills_docs / session logs (ADR-007 effective
mastery, PAR-01/02). No IO, no fixtures needed beyond plain dicts/dates.
"""
from __future__ import annotations

import math
from datetime import date, timedelta

from engine import config, report


TODAY = date(2026, 7, 7)


def _skill(mastery=50, introduced=True, exposures=3, last_practiced=None, decay=0.5):
    return {
        "mastery": mastery,
        "introduced": introduced,
        "exposures": exposures,
        "last_practiced": last_practiced,
        "decay_per_day": decay,
    }


def _skills_doc(overrides: dict) -> dict:
    """Build a skills_doc with only the given skill ids present (others skipped)."""
    return {"skills": overrides}


# ---------------------------------------------------------------------------
# skill_summary
# ---------------------------------------------------------------------------


def test_skill_summary_one_entry_per_skill_in_config_order():
    doc = _skills_doc({sid: _skill() for sid in config.SKILL_IDS})
    summary = report.skill_summary(doc, TODAY)
    assert [s["id"] for s in summary] == list(config.SKILL_IDS)


def test_skill_summary_entry_shape_and_label():
    doc = _skills_doc({"letter_orientation": _skill(mastery=42, introduced=True, exposures=5)})
    summary = report.skill_summary(doc, TODAY)
    assert len(summary) == 1
    s = summary[0]
    assert s["id"] == "letter_orientation"
    assert s["label"] == report.SKILL_LABELS["letter_orientation"]
    assert s["mastery"] == 42
    assert s["introduced"] is True
    assert s["exposures"] == 5
    assert set(s.keys()) == {"id", "label", "mastery", "introduced", "mastered", "exposures"}


def test_skill_summary_applies_decay_via_effective_mastery():
    # last_practiced 10 days ago, decay_per_day=0.5 -> effective = 50 - 5 = 45
    last = (TODAY - timedelta(days=10)).isoformat()
    doc = _skills_doc({"blends": _skill(mastery=50, last_practiced=last, decay=0.5)})
    summary = report.skill_summary(doc, TODAY)
    assert summary[0]["mastery"] == 45.0


def test_skill_summary_no_decay_when_never_practiced():
    doc = _skills_doc({"blends": _skill(mastery=50, last_practiced=None)})
    summary = report.skill_summary(doc, TODAY)
    assert summary[0]["mastery"] == 50.0


def test_skill_summary_mastered_true_when_effective_at_or_above_threshold():
    doc = _skills_doc({"heart_words": _skill(mastery=config.MASTERY_THRESHOLD, last_practiced=None)})
    summary = report.skill_summary(doc, TODAY)
    assert summary[0]["mastered"] is True


def test_skill_summary_mastered_false_when_below_threshold():
    doc = _skills_doc({"heart_words": _skill(mastery=config.MASTERY_THRESHOLD - 1, last_practiced=None)})
    summary = report.skill_summary(doc, TODAY)
    assert summary[0]["mastered"] is False


def test_skill_summary_mastered_reflects_decay_not_stored_mastery():
    # stored mastery is above threshold, but decay pushes effective below it
    last = (TODAY - timedelta(days=30)).isoformat()
    doc = _skills_doc(
        {"heart_words": _skill(mastery=config.MASTERY_THRESHOLD + 1, last_practiced=last, decay=1.2)}
    )
    summary = report.skill_summary(doc, TODAY)
    assert summary[0]["mastered"] is False


def test_skill_summary_skips_skill_missing_from_doc():
    partial = {sid: _skill() for sid in config.SKILL_IDS if sid != "magic_e"}
    doc = _skills_doc(partial)
    summary = report.skill_summary(doc, TODAY)
    ids = [s["id"] for s in summary]
    assert "magic_e" not in ids
    assert len(summary) == len(config.SKILL_IDS) - 1


# ---------------------------------------------------------------------------
# weakest_introduced
# ---------------------------------------------------------------------------


def _summary_entry(id_, mastery, introduced=True):
    return {"id": id_, "label": id_, "mastery": mastery, "introduced": introduced, "mastered": False, "exposures": 1}


def test_weakest_introduced_returns_n_lowest_sorted_ascending():
    summary = [
        _summary_entry("a", 80),
        _summary_entry("b", 20),
        _summary_entry("c", 50),
        _summary_entry("d", 10),
    ]
    result = report.weakest_introduced(summary, n=3)
    assert [s["id"] for s in result] == ["d", "b", "c"]
    assert [s["mastery"] for s in result] == [10, 20, 50]


def test_weakest_introduced_default_n_is_3():
    summary = [_summary_entry(str(i), i * 10) for i in range(5)]
    result = report.weakest_introduced(summary)
    assert len(result) == 3


def test_weakest_introduced_excludes_not_introduced():
    summary = [
        _summary_entry("a", 5, introduced=False),
        _summary_entry("b", 50, introduced=True),
    ]
    result = report.weakest_introduced(summary, n=3)
    assert [s["id"] for s in result] == ["b"]


def test_weakest_introduced_fewer_than_n_when_fewer_introduced():
    summary = [_summary_entry("a", 30, introduced=True)]
    result = report.weakest_introduced(summary, n=3)
    assert len(result) == 1


def test_weakest_introduced_empty_when_none_introduced():
    summary = [_summary_entry("a", 30, introduced=False)]
    result = report.weakest_introduced(summary, n=3)
    assert result == []


def test_weakest_introduced_empty_input():
    assert report.weakest_introduced([], n=3) == []


# ---------------------------------------------------------------------------
# radar_points
# ---------------------------------------------------------------------------


def test_radar_points_axes_and_polygon_counts_match_summary():
    summary = [_summary_entry(str(i), mastery=50) for i in range(14)]
    radar = report.radar_points(summary)
    assert len(radar["axes"]) == 14
    assert len(radar["polygon"].split(" ")) == 14
    assert set(radar.keys()) == {"size", "center", "radius", "axes", "polygon", "rings"}
    assert len(radar["rings"]) == 4


def test_radar_points_zero_mastery_sits_at_center():
    summary = [_summary_entry("a", mastery=0), _summary_entry("b", mastery=0)]
    radar = report.radar_points(summary)
    px, py = (float(v) for v in radar["polygon"].split(" ")[0].split(","))
    dist = math.hypot(px - radar["center"], py - radar["center"])
    assert dist < 0.5  # essentially at the center (float rounding tolerance)


def test_radar_points_full_mastery_sits_on_outer_radius():
    summary = [_summary_entry("a", mastery=100), _summary_entry("b", mastery=100)]
    radar = report.radar_points(summary)
    px, py = (float(v) for v in radar["polygon"].split(" ")[0].split(","))
    dist = math.hypot(px - radar["center"], py - radar["center"])
    assert abs(dist - radar["radius"]) < 0.5


def test_radar_points_custom_size_and_margin():
    summary = [_summary_entry("a", mastery=50)]
    radar = report.radar_points(summary, size=200, margin=20)
    assert radar["size"] == 200
    assert radar["center"] == 100.0
    assert radar["radius"] == 80.0


# ---------------------------------------------------------------------------
# recent_errors
# ---------------------------------------------------------------------------


def _log(date_str, items):
    return {"date": date_str, "items": items}


def _item(target, skill_id, attempts):
    return {"target": target, "skill_id": skill_id, "attempts": attempts}


def _attempt(attempt, phase="first", correct=False, tags=None):
    return {"attempt": attempt, "phase": phase, "correct": correct, "tags": tags or []}


def test_recent_errors_only_first_try_incorrect():
    logs = [
        _log(
            "2026-07-01",
            [
                _item(
                    "cat",
                    "short_vowels",
                    [
                        _attempt("cet", phase="first", correct=False, tags=["reversal"]),
                        _attempt("cat", phase="retry", correct=True),
                    ],
                ),
                _item(
                    "dog",
                    "short_vowels",
                    [_attempt("dog", phase="first", correct=True)],
                ),
            ],
        )
    ]
    result = report.recent_errors(logs)
    assert len(result) == 1
    assert result[0] == {
        "date": "2026-07-01",
        "target": "cat",
        "attempt": "cet",
        "tags": ["reversal"],
        "skill": "short_vowels",
    }


def test_recent_errors_excludes_correct_attempts():
    logs = [_log("2026-07-01", [_item("cat", "short_vowels", [_attempt("cat", phase="first", correct=True)])])]
    assert report.recent_errors(logs) == []


def test_recent_errors_excludes_retry_phase_even_if_incorrect():
    logs = [_log("2026-07-01", [_item("cat", "short_vowels", [_attempt("cog", phase="retry", correct=False)])])]
    assert report.recent_errors(logs) == []


def test_recent_errors_newest_first_given_oldest_first_input():
    logs = [
        _log("2026-07-01", [_item("old", "blends", [_attempt("xxx", phase="first", correct=False)])]),
        _log("2026-07-05", [_item("new", "blends", [_attempt("yyy", phase="first", correct=False)])]),
    ]
    result = report.recent_errors(logs)
    assert [r["target"] for r in result] == ["new", "old"]
    assert [r["date"] for r in result] == ["2026-07-05", "2026-07-01"]


def test_recent_errors_respects_limit():
    items = [_item(f"w{i}", "blends", [_attempt(f"x{i}", phase="first", correct=False)]) for i in range(5)]
    logs = [_log("2026-07-01", items)]
    result = report.recent_errors(logs, limit=2)
    assert len(result) == 2


def test_recent_errors_default_limit_is_20():
    items = [_item(f"w{i}", "blends", [_attempt(f"x{i}", phase="first", correct=False)]) for i in range(25)]
    logs = [_log("2026-07-01", items)]
    result = report.recent_errors(logs)
    assert len(result) == 20


def test_recent_errors_empty_input():
    assert report.recent_errors([]) == []


def test_recent_errors_tags_default_to_empty_list():
    logs = [
        _log(
            "2026-07-01",
            [_item("cat", "short_vowels", [{"attempt": "cet", "phase": "first", "correct": False}])],
        )
    ]
    result = report.recent_errors(logs)
    assert result[0]["tags"] == []
