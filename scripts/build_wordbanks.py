"""Build data/word_bank/*.json from scripts/raw_words.py.

Computes the schema fields (phonemes, difficulty, distractors) via engine.phonics,
and MERGES with any existing bank so hand-crafted emoji/phrase/sentence/tricky_letters
(and sound-based phonemes for heart words) are preserved. phrase/sentence/emoji are
left null on new words for AI enrichment later.

Run from the repo root:  .venv/bin/python scripts/build_wordbanks.py
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine import phonics  # noqa: E402
from scripts.raw_words import RAW  # noqa: E402

WORD_BANK_DIR = ROOT / "data" / "word_bank"
_CONFUSABLES = ["b", "d", "p", "q", "m", "w"]  # reversal-practice distractors first
_FILLERS = list("aeioustnrlkg")


def _distractors(word: str, rng: random.Random, k: int = 2) -> list[str]:
    """A couple of tile distractors not already in the word — favour b/d/p/q
    confusables (they double as reversal practice)."""
    letters = set(word.lower())
    pool = [c for c in _CONFUSABLES if c not in letters] + [c for c in _FILLERS if c not in letters]
    seen: list[str] = []
    for c in pool:
        if c not in seen:
            seen.append(c)
    rng.shuffle(seen)
    return seen[:k]


def build_pattern(pattern: str, words: list[str], existing: dict[str, dict]) -> list[dict]:
    rng = random.Random(pattern)  # deterministic per pattern
    seen: set[str] = set()
    entries: list[dict] = []
    for raw in words:
        w = raw.strip().lower()
        if not w.isalpha() or w in seen:
            continue
        seen.add(w)
        prev = existing.get(w, {})
        phonemes = prev.get("phonemes") or phonics.segment_graphemes(w)
        entries.append(
            {
                "word": w,
                "phonemes": phonemes,
                "pattern": pattern,
                "difficulty": phonics.difficulty(w, pattern, phonemes),
                "tricky_letters": prev.get("tricky_letters", []),
                "phrase": prev.get("phrase"),
                "sentence": prev.get("sentence"),
                "emoji": prev.get("emoji", ""),
                "distractors": prev.get("distractors") or _distractors(w, rng),
            }
        )
    entries.sort(key=lambda e: (e["difficulty"], e["word"]))
    return entries


def load_existing(pattern: str) -> dict[str, dict]:
    path = WORD_BANK_DIR / f"{pattern}.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {w["word"]: w for w in data.get("words", [])}


def main() -> None:
    WORD_BANK_DIR.mkdir(parents=True, exist_ok=True)
    total = 0
    for pattern, words in RAW.items():
        entries = build_pattern(pattern, words, load_existing(pattern))
        out = {
            "pattern": pattern,
            "note": f"{len(entries)} words. Built by scripts/build_wordbanks.py; "
            "phrase/sentence/emoji enriched by AI (see docs). difficulty = engine.phonics (1-5).",
            "words": entries,
        }
        path = WORD_BANK_DIR / f"{pattern}.json"
        path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        by_diff = {}
        for e in entries:
            by_diff[e["difficulty"]] = by_diff.get(e["difficulty"], 0) + 1
        print(f"{pattern:18} {len(entries):>4} words  difficulty {dict(sorted(by_diff.items()))}")
        total += len(entries)
    print(f"{'TOTAL':18} {total:>4} words across {len(RAW)} patterns")


if __name__ == "__main__":
    main()
