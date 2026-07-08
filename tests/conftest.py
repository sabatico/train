"""Shared fixtures for the Spell Quest test suite.

CRITICAL GOTCHA (see task brief): `store.DATA_ROOT` and `store.WORD_BANK_DIR` are
module-level Paths computed from $SPELLQUEST_DATA_DIR at *import time*. Setting the
env var alone does nothing once the module is imported, so every fixture here
monkeypatches `store.DATA_ROOT` / `store.WORD_BANK_DIR` directly at runtime.

The word bank (`data/word_bank/`, holding skill_graph.json + per-pattern word
lists) is git-tracked *source* that lives under the data root. A temp data dir
with no `word_bank/` makes `load_skill_graph()` return `{}`, which makes
`default_skills` mark ALL 14 skills as "introduced" (empty prereqs list ==
vacuously introduced) -- silently invalidating any assertion about which skills
start locked. So every temp data root here is seeded by copying the real
`data/word_bank/` tree in.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
REAL_WORD_BANK = REPO_ROOT / "data" / "word_bank"

sys.path.insert(0, str(REPO_ROOT))

from engine import store  # noqa: E402


@pytest.fixture
def data_root(tmp_path, monkeypatch):
    """A clean temp data root, seeded with the real (git-tracked) word_bank/,
    with store.DATA_ROOT / store.WORD_BANK_DIR monkeypatched to point at it."""
    root = tmp_path / "data"
    root.mkdir()
    shutil.copytree(REAL_WORD_BANK, root / "word_bank")
    monkeypatch.setattr(store, "DATA_ROOT", root)
    monkeypatch.setattr(store, "WORD_BANK_DIR", root / "word_bank")
    return root


@pytest.fixture
def empty_data_root(tmp_path, monkeypatch):
    """A clean temp data root with NO word_bank/ seeded — for exercising the
    "missing content" defaults (e.g. load_skill_graph() == {})."""
    root = tmp_path / "data_empty"
    root.mkdir()
    monkeypatch.setattr(store, "DATA_ROOT", root)
    monkeypatch.setattr(store, "WORD_BANK_DIR", root / "word_bank")
    return root


@pytest.fixture
def bootstrapped_student(data_root):
    """A bootstrapped student ("kiddo") in a seeded temp data root. Returns the
    student_id string for reuse across tests."""
    student_id = "kiddo"
    store.bootstrap_student(student_id)
    return student_id
