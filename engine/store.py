"""The ONLY module that touches the file database (ADR-001/006).

Guarantees (invariant #1 — no child data loss):
  * every write is atomic: temp file in the same dir → os.replace (POSIX-atomic
    rename), with fsync, so a crash never leaves a half-written file;
  * reads of a missing file return a typed default, never crash — the app must
    run on a brand-new student directory.

Every public function takes `student_id` first (ADR-004 seam): v1 always passes
"default", but no code assumes a single student, so the Stage-2 DB swap is a
reimplementation of THIS module with callers untouched.
"""
from __future__ import annotations

import copy
import json
import os
import re
import tempfile
from datetime import date
from pathlib import Path

from . import models

# Data root is overridable via env so tests (and Stage-2 hosts) can redirect it.
DATA_ROOT = Path(os.environ.get("SPELLQUEST_DATA_DIR", "data"))
WORD_BANK_DIR = DATA_ROOT / "word_bank"

# doc name -> (filename, default factory). The whole-file read-modify-write docs.
_DOCS: dict[str, tuple[str, object]] = {
    "profile": ("profile.json", models.default_profile),
    "rewards": ("rewards.json", models.default_rewards),
    # "skills" is special-cased (its default needs the skill graph) — see load().
}

_SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


# ---------------------------------------------------------------- paths & safety
def _safe_student_id(student_id: str) -> str:
    """Reject anything that isn't a plain slug — blocks path traversal (`../`,
    absolute paths, separators). Matters now for correctness and later for
    multi-tenant isolation (ADR-004)."""
    if not isinstance(student_id, str) or not _SAFE_ID.match(student_id):
        raise ValueError(f"invalid student_id: {student_id!r}")
    return student_id


def student_dir(student_id: str) -> Path:
    return DATA_ROOT / "students" / _safe_student_id(student_id)


# ----------------------------------------------------------------- atomic IO
def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)  # atomic on POSIX
    except BaseException:
        # never leave the temp file behind on failure
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _write_json(path: Path, data) -> None:
    _atomic_write(path, json.dumps(data, ensure_ascii=False, indent=2))


def _read_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


# ----------------------------------------------------------------- whole-file docs
def load(student_id: str, doc: str):
    """Read a per-student document, or a fresh default if it doesn't exist yet."""
    if doc == "skills":
        path = student_dir(student_id) / "skills.json"
        if path.exists():
            return _read_json(path)
        return models.default_skills(load_skill_graph())
    if doc not in _DOCS:
        raise KeyError(f"unknown doc: {doc!r}")
    filename, default_factory = _DOCS[doc]
    path = student_dir(student_id) / filename
    if path.exists():
        return _read_json(path)
    return default_factory()


def save(student_id: str, doc: str, data) -> None:
    if doc == "skills":
        filename = "skills.json"
    elif doc in _DOCS:
        filename = _DOCS[doc][0]
    else:
        raise KeyError(f"unknown doc: {doc!r}")
    _write_json(student_dir(student_id) / filename, data)


# ----------------------------------------------------------------- teacher notebook
def append_memory(student_id: str, entry: str, on: date | None = None) -> None:
    """Append a dated observation to the agent's notebook (ADR-006/012)."""
    day = (on or date.today()).isoformat()
    path = student_dir(student_id) / "memory.md"
    prior = path.read_text(encoding="utf-8") if path.exists() else "# Teacher notebook\n"
    _atomic_write(path, f"{prior.rstrip()}\n\n**{day}** — {entry.strip()}\n")


def read_memory(student_id: str) -> str:
    path = student_dir(student_id) / "memory.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""


# ----------------------------------------------------------------- sessions (ADR-009)
def load_current_session(student_id: str) -> dict | None:
    path = student_dir(student_id) / "sessions" / "current.json"
    return _read_json(path) if path.exists() else None


def save_current_session(student_id: str, data: dict) -> None:
    _write_json(student_dir(student_id) / "sessions" / "current.json", data)


def clear_current_session(student_id: str) -> None:
    path = student_dir(student_id) / "sessions" / "current.json"
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def write_session_log(student_id: str, log: dict, on: date | None = None) -> str:
    """Persist a completed session as sessions/<date>.json. Returns the date key."""
    day = (on or date.today()).isoformat()
    _write_json(student_dir(student_id) / "sessions" / f"{day}.json", log)
    return day


def list_session_logs(student_id: str) -> list[str]:
    """Sorted date keys of completed sessions (excludes current.json)."""
    sdir = student_dir(student_id) / "sessions"
    if not sdir.exists():
        return []
    return sorted(p.stem for p in sdir.glob("*.json") if p.stem != "current")


# ----------------------------------------------------------------- shared content
def load_word_bank(pattern: str) -> list[dict]:
    """Read a curated word list (shared content, read-only, git-tracked)."""
    path = WORD_BANK_DIR / f"{_safe_student_id(pattern)}.json"
    if not path.exists():
        return []
    data = _read_json(path)
    return data.get("words", []) if isinstance(data, dict) else data


def load_skill_graph() -> dict[str, list[str]]:
    path = WORD_BANK_DIR / "skill_graph.json"
    return _read_json(path) if path.exists() else {}


# ----------------------------------------------------------------- bootstrap
def bootstrap_student(student_id: str) -> None:
    """Lay down a fresh student's default docs. Idempotent — never overwrites
    existing data (invariant #1)."""
    sdir = student_dir(student_id)
    (sdir / "sessions").mkdir(parents=True, exist_ok=True)
    (sdir / "logs").mkdir(parents=True, exist_ok=True)
    graph = load_skill_graph()
    defaults = {
        "profile": models.default_profile(),
        "skills": models.default_skills(graph),
        "rewards": models.default_rewards(),
    }
    for doc, data in defaults.items():
        filename = "skills.json" if doc == "skills" else _DOCS[doc][0]
        if not (sdir / filename).exists():
            _write_json(sdir / filename, copy.deepcopy(data))
