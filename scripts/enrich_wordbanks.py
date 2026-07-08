"""Batch-enrich the word banks with AI-generated phrase/sentence/emoji (T-015).

Fills ONLY the missing fields (phrase/sentence null, or emoji "") so it's
resumable and never overwrites hand-crafted content. Writes each bank back
atomically. Requires DEEPSEEK_API_KEY (uses agent.enrich → DeepSeek).

Run from the repo root:  .venv/bin/python scripts/enrich_wordbanks.py [--limit N]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent import client, enrich  # noqa: E402

WORD_BANK_DIR = ROOT / "data" / "word_bank"
BATCH = 20


def _needs_enrichment(entry: dict) -> bool:
    return not entry.get("phrase") or not entry.get("sentence") or not entry.get("emoji")


def enrich_bank(path: Path, limit: int | None) -> tuple[int, int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    words = data["words"]
    todo = [e for e in words if _needs_enrichment(e)]
    if limit is not None:
        todo = todo[:limit]
    if not todo:
        return 0, 0

    by_word = {e["word"]: e for e in words}
    filled = 0
    for i in range(0, len(todo), BATCH):
        chunk = [e["word"] for e in todo[i : i + BATCH]]
        try:
            results = enrich.enrich_batch(chunk)
        except client.AgentError as exc:
            print(f"    batch failed ({exc}); skipping", flush=True)
            continue
        for word, e in results.items():
            entry = by_word.get(word)
            if not entry:
                continue
            entry["phrase"] = entry.get("phrase") or e["phrase"]
            entry["sentence"] = entry.get("sentence") or e["sentence"]
            entry["emoji"] = entry.get("emoji") or e["emoji"]
            filled += 1
        print(f"    {min(i + BATCH, len(todo))}/{len(todo)} …", flush=True)
        time.sleep(0.3)

    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return len(todo), filled


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="max words per bank (for testing)")
    args = ap.parse_args()
    if not client.is_configured():
        sys.exit("DEEPSEEK_API_KEY not set — cannot enrich.")

    total_todo = total_filled = 0
    for path in sorted(WORD_BANK_DIR.glob("*.json")):
        if path.stem == "skill_graph":
            continue
        print(f"{path.stem} …", flush=True)
        todo, filled = enrich_bank(path, args.limit)
        print(f"  {path.stem}: enriched {filled}/{todo}", flush=True)
        total_todo += todo
        total_filled += filled
    print(f"\nTOTAL: enriched {total_filled}/{total_todo} words")


if __name__ == "__main__":
    main()
