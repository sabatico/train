"""Generate a verified word-picture SVG per drawable word (owner idea 2026-07-10).

Pipeline (resumable — safe to re-run):
  classify → generate → (human/lead visual verify, separate) → wire.

This script does classify + generate. It writes:
  static/img/words/<word>.svg      the generated art (safe/sanitized)
  data/word_images.json            manifest: {word: {drawable, brief, status}}
                                   status: ok | skip(=not drawable) | fail | rejected
Verification (rendering the gallery + marking 'rejected') is the lead's visual
pass; re-running regenerates anything not 'ok'/'skip'/'rejected'.

Run:  .venv/bin/python scripts/gen_word_svgs.py [--regen] [--limit N]
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent import client, svg_art  # noqa: E402

IMG_DIR = ROOT / "static" / "img" / "words"
MANIFEST = ROOT / "data" / "word_images.json"
WORD_BANK_DIR = ROOT / "data" / "word_bank"
CLASSIFY_BATCH = 25


def all_words() -> list[str]:
    words: set[str] = set()
    for f in glob.glob(str(WORD_BANK_DIR / "*.json")):
        if f.endswith("skill_graph.json"):
            continue
        for w in json.loads(Path(f).read_text(encoding="utf-8")).get("words", []):
            words.add(w["word"].lower())
    return sorted(words)


def load_manifest() -> dict[str, dict]:
    return json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}


def save_manifest(m: dict) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    tmp = MANIFEST.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(MANIFEST)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--regen", action="store_true", help="redo words marked 'rejected'")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    if not client.is_configured():
        sys.exit("DEEPSEEK_API_KEY not set.")
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    words = all_words()

    # 1) classify anything not yet classified
    todo_classify = [w for w in words if w not in manifest]
    for i in range(0, len(todo_classify), CLASSIFY_BATCH):
        chunk = todo_classify[i : i + CLASSIFY_BATCH]
        try:
            verdicts = svg_art.classify_words(chunk)
        except client.AgentError as exc:
            print(f"  classify batch failed ({exc})")
            continue
        for w in chunk:
            v = verdicts.get(w, {"drawable": False, "draw": ""})
            manifest[w] = {"drawable": v["drawable"], "brief": v["draw"],
                           "status": "pending" if v["drawable"] else "skip"}
        save_manifest(manifest)
        print(f"  classified {min(i + CLASSIFY_BATCH, len(todo_classify))}/{len(todo_classify)}")

    # 2) generate for drawable words that need art
    def needs_gen(w: str) -> bool:
        m = manifest.get(w)
        if not m:  # a classify batch dropped it — leave for the next classify pass
            return False
        if not m["drawable"]:
            return False
        if m["status"] == "ok" and (IMG_DIR / f"{w}.svg").exists():
            return False
        if m["status"] == "rejected" and not args.regen:
            return False
        return True

    gen = [w for w in words if needs_gen(w)]
    if args.limit is not None:
        gen = gen[: args.limit]
    print(f"{len(gen)} words to draw")
    made = failed = 0
    for w in gen:
        try:
            svg = svg_art.generate_svg(w, hint=manifest[w]["brief"])
            (IMG_DIR / f"{w}.svg").write_text(svg, encoding="utf-8")
            manifest[w]["status"] = "ok"
            made += 1
        except (client.AgentError, ValueError) as exc:
            manifest[w]["status"] = "fail"
            failed += 1
            print(f"  {w}: {exc}")
        if (made + failed) % 20 == 0:
            save_manifest(manifest)
            print(f"  drawn {made}, failed {failed} / {len(gen)}")
        time.sleep(0.1)
    save_manifest(manifest)
    drawable = sum(1 for m in manifest.values() if m["drawable"])
    ok = sum(1 for m in manifest.values() if m["status"] == "ok")
    print(f"\nDONE: {len(words)} words | {drawable} drawable | {ok} have art | {failed} failed this run")


if __name__ == "__main__":
    main()
