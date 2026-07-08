"""Parent dashboard data + the rose-of-winds radar geometry (PAR-01/02, PLAN §2).

Pure functions over stored state (no IO here beyond what the caller passes in),
so the radar and summaries are deterministic and testable. The app renders these
server-side (the parent screens are plain server-rendered pages — DESIGN_BRIEF §7).
"""
from __future__ import annotations

import math
from datetime import date

from . import config, skills as skills_mod

# Friendly labels for the 14 skill ids (parent-facing).
SKILL_LABELS = {
    "letter_orientation": "b/d letters",
    "phoneme_segmentation": "sounds",
    "short_vowels": "short vowels",
    "blends": "blends",
    "digraphs": "digraphs",
    "magic_e": "magic e",
    "vowel_teams": "vowel teams",
    "r_controlled": "r-controlled",
    "doubling_endings": "doubling",
    "heart_words": "heart words",
    "suffixes": "suffixes",
    "word_sequencing": "sequencing",
    "phrase_dictation": "phrases",
    "sentence_writing": "sentences",
}


def skill_summary(skills_doc: dict, today: date) -> list[dict]:
    """Per-skill effective mastery + status, in the fixed teaching order."""
    out = []
    skills = skills_doc["skills"]
    for sid in config.SKILL_IDS:
        s = skills.get(sid)
        if not s:
            continue
        eff = skills_mod.effective_mastery(s, today)
        out.append(
            {
                "id": sid,
                "label": SKILL_LABELS.get(sid, sid),
                "mastery": round(eff, 1),
                "introduced": s["introduced"],
                "mastered": eff >= config.MASTERY_THRESHOLD,
                "exposures": s["exposures"],
            }
        )
    return out


def weakest_introduced(summary: list[dict], n: int = 3) -> list[dict]:
    """The n lowest-mastery introduced skills — 'what to work on'."""
    intro = [s for s in summary if s["introduced"]]
    return sorted(intro, key=lambda s: s["mastery"])[:n]


def radar_points(summary: list[dict], *, size: int = 320, margin: int = 44) -> dict:
    """SVG geometry for the rose-of-winds radar: the outer axis points (for labels)
    and the mastery polygon points, as 'x,y' strings ready for an SVG <polygon>."""
    n = len(summary)
    cx = cy = size / 2
    radius = size / 2 - margin
    axes, poly = [], []
    for i, s in enumerate(summary):
        angle = -math.pi / 2 + (2 * math.pi * i / n)  # start at top, clockwise
        ax = cx + radius * math.cos(angle)
        ay = cy + radius * math.sin(angle)
        r = radius * (s["mastery"] / 100.0)
        px = cx + r * math.cos(angle)
        py = cy + r * math.sin(angle)
        axes.append({"x": round(ax, 1), "y": round(ay, 1), "label": s["label"], "mastery": s["mastery"]})
        poly.append(f"{round(px, 1)},{round(py, 1)}")
    return {
        "size": size,
        "center": round(cx, 1),
        "radius": round(radius, 1),
        "axes": axes,
        "polygon": " ".join(poly),
        "rings": [round(radius * f, 1) for f in (0.25, 0.5, 0.75, 1.0)],
    }


def recent_errors(session_logs: list[dict], limit: int = 20) -> list[dict]:
    """Flatten recent misses across sessions for the parent error log (PAR-02).
    Parent-only surface — the child's raw misspellings ARE shown here (never to
    the child). Newest first."""
    errors = []
    for log in reversed(session_logs):  # logs passed newest-last → iterate newest-first
        for item in log.get("items", []):
            for att in item.get("attempts", []):
                if att.get("phase") == "first" and not att.get("correct"):
                    errors.append(
                        {
                            "date": log.get("date"),
                            "target": item.get("target"),
                            "attempt": att.get("attempt"),
                            "tags": att.get("tags", []),
                            "skill": item.get("skill_id"),
                        }
                    )
                    if len(errors) >= limit:
                        return errors
    return errors
