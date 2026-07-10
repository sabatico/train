"""Audit every word's emoji across the banks with the strict judge (agent/emoji_review).

Applies verdicts in place (atomic writes), prints every change for owner review.
Only the `emoji` field is ever touched. Run:  .venv/bin/python scripts/review_emoji.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent import client, emoji_review  # noqa: E402

WORD_BANK_DIR = ROOT / "data" / "word_bank"
BATCH = 25


def main() -> None:
    if not client.is_configured():
        sys.exit("DEEPSEEK_API_KEY not set.")
    total = changed = removed = replaced = 0
    for path in sorted(WORD_BANK_DIR.glob("*.json")):
        if path.stem == "skill_graph":
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        words = data["words"]
        rows = [{"word": w["word"], "emoji": w.get("emoji", ""), "phrase": w.get("phrase") or ""} for w in words]
        verdicts: dict[str, str] = {}
        for i in range(0, len(rows), BATCH):
            chunk = rows[i : i + BATCH]
            try:
                verdicts.update(emoji_review.review_batch(chunk))
            except client.AgentError as exc:
                print(f"  batch failed ({exc}); those words keep their current emoji")
            time.sleep(0.2)
        by_word = {w["word"]: w for w in words}
        for word, new_emoji in verdicts.items():
            by_word[word]["emoji"] = new_emoji

        # PASS 2 — back-translation: every remaining image must make a child say
        # THIS word when shown alone; anything else is a harmful cue → removed.
        remaining = [(w["word"], w["emoji"]) for w in words if w.get("emoji")]
        failed: set[str] = set()
        for i in range(0, len(remaining), BATCH):
            chunk = remaining[i : i + BATCH]
            try:
                failed.update(emoji_review.verify_batch(chunk))
            except client.AgentError as exc:
                print(f"  reverse batch failed ({exc}); those images kept unverified")
            time.sleep(0.2)
        for word in failed:
            by_word[word]["emoji"] = ""

        for w in words:
            old = next((r["emoji"] for r in rows if r["word"] == w["word"]), "")
            new = w.get("emoji", "")
            if old == new:
                continue
            changed += 1
            if new:
                replaced += 1
                print(f"  {w['word']:12} {old or '∅':4} → {new}")
            else:
                removed += 1
                print(f"  {w['word']:12} {old or '∅':4} → (no image)")
        total += len(words)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(path)
        print(f"{path.stem}: done")
    print(f"\nTOTAL: {total} words audited — {changed} changed ({replaced} replaced, {removed} images removed)")


if __name__ == "__main__":
    main()
