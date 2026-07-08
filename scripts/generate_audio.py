"""Pre-generate natural-voice audio clips for every word bank word (T-014).

Owner decision 2026-07-08: replace the robotic browser TTS with pre-generated
OpenAI TTS clips, cached as static files (natural voice, instant, offline, ~free
per play). The frontend (static/js/speech.js) prefers these and falls back to
browser TTS for any missing clip — so this is purely additive.

Idempotent + resumable: skips words that already have a clip. Requires
OPENAI_API_KEY (a SECOND provider, TTS only — see ADR-013 / third-party-services).

Run from repo root:  .venv/bin/python scripts/generate_audio.py [--voice nova] [--limit N]
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

from agent import voice  # noqa: E402

AUDIO_DIR = ROOT / "static" / "audio"
WORD_BANK_DIR = ROOT / "data" / "word_bank"


def all_words() -> list[str]:
    words: set[str] = set()
    for f in glob.glob(str(WORD_BANK_DIR / "*.json")):
        if f.endswith("skill_graph.json"):
            continue
        for w in json.loads(Path(f).read_text(encoding="utf-8")).get("words", []):
            words.add(w["word"].lower())
    return sorted(words)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default=voice.VOICE)
    ap.add_argument("--instructions", default=voice.INSTRUCTIONS)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    if not voice.is_configured():
        sys.exit("OPENAI_API_KEY not set — cannot generate audio (see ADR-013).")

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    words = all_words()
    todo = [w for w in words if not (AUDIO_DIR / f"{w}.mp3").exists()]
    if args.limit is not None:
        todo = todo[: args.limit]
    print(f"{len(words)} words, {len(todo)} to generate ({voice.MODEL}, voice={args.voice})")

    made = 0
    for w in todo:
        try:
            data = voice.synthesize(w, voice=args.voice, instructions=args.instructions)
        except voice.VoiceError as exc:
            print(f"  {w}: FAILED ({exc}); skipping")
            continue
        (AUDIO_DIR / f"{w}.mp3").write_bytes(data)
        made += 1
        if made % 25 == 0:
            print(f"  {made}/{len(todo)} …")
        time.sleep(0.05)
    print(f"done: generated {made} clips into static/audio/")


if __name__ == "__main__":
    main()
