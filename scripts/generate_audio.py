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
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import certifi

ROOT = Path(__file__).resolve().parent.parent
AUDIO_DIR = ROOT / "static" / "audio"
WORD_BANK_DIR = ROOT / "data" / "word_bank"
_SSL = ssl.create_default_context(cafile=certifi.where())


def all_words() -> list[str]:
    words: set[str] = set()
    for f in glob.glob(str(WORD_BANK_DIR / "*.json")):
        if f.endswith("skill_graph.json"):
            continue
        for w in json.loads(Path(f).read_text(encoding="utf-8")).get("words", []):
            words.add(w["word"].lower())
    return sorted(words)


def tts(word: str, voice: str, speed: float, timeout: float = 30.0) -> bytes:
    """One OpenAI TTS call → mp3 bytes."""
    req = urllib.request.Request(
        "https://api.openai.com/v1/audio/speech",
        data=json.dumps(
            {"model": "tts-1", "voice": voice, "input": word, "response_format": "mp3", "speed": speed}
        ).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout, context=_SSL) as resp:
        return resp.read()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default=os.environ.get("OPENAI_TTS_VOICE", "nova"))
    ap.add_argument("--speed", type=float, default=0.9)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY not set — cannot generate audio (see ADR-013).")

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    words = all_words()
    todo = [w for w in words if not (AUDIO_DIR / f"{w}.mp3").exists()]
    if args.limit is not None:
        todo = todo[: args.limit]
    print(f"{len(words)} words, {len(todo)} to generate (voice={args.voice})")

    made = 0
    for w in todo:
        try:
            data = tts(w, args.voice, args.speed)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            print(f"  {w}: FAILED ({type(exc).__name__}); skipping")
            continue
        (AUDIO_DIR / f"{w}.mp3").write_bytes(data)
        made += 1
        if made % 25 == 0:
            print(f"  {made}/{len(todo)} …")
        time.sleep(0.05)
    print(f"done: generated {made} clips into static/audio/")


if __name__ == "__main__":
    main()
