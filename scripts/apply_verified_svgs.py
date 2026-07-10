"""Apply the lead's visual-verification verdict (2026-07-10).

After the human/lead visual pass over the generated word SVGs, this:
  1) marks REJECTED words in data/word_images.json (status='rejected'),
  2) wires entry["image"] = "words/<word>.svg" onto every word-bank entry
     whose picture survived verification (manifest status=='ok' and NOT rejected),
     and clears entry["image"] for everyone else (fall back to emoji/placeholder).

Idempotent — safe to re-run. Writes are atomic (tmp + rename), matching the
data-safety invariant. word_bank/ is curated source, so editing it here is fine.

Run:  .venv/bin/python scripts/apply_verified_svgs.py
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data" / "word_images.json"
WORD_BANK_DIR = ROOT / "data" / "word_bank"

# Rejected in the lead's visual pass: picture is ambiguous or reads as a
# different word. An ambiguous picture actively misleads a dyslexic reader,
# so the bar is "unambiguous or it goes" -> these fall back to no-picture.
REJECTED = """
ball bead beds beg bend bill blow bog boil bone
braid case chin chip
claw clay clip cloth coach cuff curb curl curve dad
dash deck den dip dirt dot dug fall
fat fell fight file fin fur fuzz goal grain gum
gun ham hat hats hay herd hide hit hole hop hops horn
junk kick kit lap leg lid line map melt
mess mint mud neck nine nod oil one pat
peg pet pink pit pod poke pond pool pop puff pull purple
rag ran ray red rib rice ride rip rod roll rope run runs sat saw
shin sip sit sits six skip slip smell smoke snap sniff snow sob soil
spark spill spin sport spot stand stem step stir stone street sub tag tail tall tap tape
thirty three tile tin tip toast top toy trap tray tube tug turn twirl two vine wag wait
wake walk wave wet whip wig wine wink wire wood yam yard zoo
""".split()


def atomic_write(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def main() -> None:
    rejected = set(REJECTED)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    # sanity: every rejected word must be an 'ok' (generated) picture
    unknown = [w for w in rejected if manifest.get(w, {}).get("status") not in ("ok", "rejected")]
    if unknown:
        raise SystemExit(f"rejects not in 'ok' state (typo?): {sorted(unknown)}")

    # 1) mark rejects in the manifest
    for w, m in manifest.items():
        if w in rejected:
            m["status"] = "rejected"
    atomic_write(MANIFEST, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

    keepers = {w for w, m in manifest.items() if m["status"] == "ok"}
    print(f"manifest: {len(rejected)} rejected, {len(keepers)} verified keepers")

    # 2) wire image field onto the banks
    wired = cleared = 0
    for f in sorted(glob.glob(str(WORD_BANK_DIR / "*.json"))):
        if f.endswith("skill_graph.json"):
            continue
        data = json.loads(Path(f).read_text(encoding="utf-8"))
        changed = False
        for entry in data.get("words", []):
            w = entry["word"].lower()
            if w in keepers:
                want = f"words/{w}.svg"
                if entry.get("image") != want:
                    entry["image"] = want
                    changed = True
                wired += 1
            elif entry.get("image"):
                del entry["image"]
                changed = True
                cleared += 1
        if changed:
            atomic_write(Path(f), json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(f"banks: wired {wired} image fields, cleared {cleared} stale ones")


if __name__ == "__main__":
    main()
