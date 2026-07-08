"""Loudness-normalize the dictation clips so they all play at the same perceived
volume (fixes the "some clips are much louder" problem — T-014 follow-up).

Uses EBU R128 loudness normalization (ffmpeg `loudnorm`, target -16 LUFS), which
measures PERCEIVED loudness with silence-gating — so a word with lots of trailing
silence isn't wrongly boosted. ffmpeg comes bundled via imageio-ffmpeg (no system
install). Rewrites each mp3 in place (atomic via temp).

Run from repo root:  .venv/bin/python scripts/normalize_audio.py [--limit N]
"""
from __future__ import annotations

import argparse
import glob
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
AUDIO_DIR = Path(__file__).resolve().parent.parent / "static" / "audio"
TARGET = "loudnorm=I=-16:TP=-1.5:LRA=11"  # speech-friendly integrated loudness


def normalize(path: Path) -> bool:
    tmp = path.with_suffix(".norm.mp3")
    cmd = [
        FF, "-y", "-i", str(path),
        "-af", TARGET,
        "-c:a", "libmp3lame", "-b:a", "128k", "-ar", "24000", "-ac", "1",
        str(tmp),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0 or not tmp.exists() or tmp.stat().st_size == 0:
        tmp.unlink(missing_ok=True)
        return False
    tmp.replace(path)
    return True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    files = sorted(Path(p) for p in glob.glob(str(AUDIO_DIR / "*.mp3")))
    if args.limit is not None:
        files = files[: args.limit]
    print(f"normalizing {len(files)} clips to {TARGET} …")
    done = failed = 0
    for i, f in enumerate(files, 1):
        if normalize(f):
            done += 1
        else:
            failed += 1
            print(f"  FAILED: {f.name}")
        if i % 100 == 0:
            print(f"  {i}/{len(files)} …")
    print(f"done: normalized {done}, failed {failed}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
