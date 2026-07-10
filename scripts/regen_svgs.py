"""Second-pass regen of the WINNABLE rejects (2026-07-10).

The first visual pass rejected 161 pictures. Most are abstract/action/relational
words that simply can't be drawn (walk, red, the) — those stay pictureless.
But some are concrete nouns that only failed because the model drew them wrong or
too generically (ball->wheel, bone->brain, wig->acorn). Those are worth one retry
with a SHARPER, more distinctive brief.

This regenerates only that curated set, writes the SVGs, and builds a single
review page (static/_review/regen.html) for the lead's second visual pass. It does
NOT change the manifest or banks — apply_verified_svgs.py does that after review.

Run:  .venv/bin/python scripts/regen_svgs.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent import client, svg_art  # noqa: E402

IMG_DIR = ROOT / "static" / "img" / "words"
OUT = ROOT / "static" / "_review"

# curated: concrete nouns with ONE canonical, unambiguous depiction + a sharp brief
BRIEFS = {
    "bead": "a single round blue bead with a hole through the center",
    "bone": "a classic white dog bone: a bar with two rounded knobs at each end",
    "braid": "a single long hair braid, three strands woven together, tied at the bottom",
    "case": "a suitcase: a rectangular case with a handle on top and two latches",
    "claw": "a single red crab pincer claw, open",
    "clip": "a silver metal paperclip",
    "fin": "a grey shark fin poking up above blue water",
    "goal": "a soccer goal: a white rectangular net frame with a soccer ball",
    "ham": "a pink cooked ham with a small white bone sticking out of one end",
    "hat": "a red baseball cap seen from the side",
    "hats": "two hats side by side: a red cap and a blue sun hat",
    "hay": "a golden cylindrical hay bale with two dark binding bands",
    "map": "a folded paper map showing winding roads and a red X mark",
    "peg": "a single wooden clothes peg (clothespin), standing upright",
    "pod": "a bright green pea pod split open showing three round peas",
    "pond": "a small round blue pond with a green lily pad and cattail reeds",
    "pool": "a rectangular swimming pool, blue water, with a white pool ladder",
    "rice": "a white bowl heaped with fluffy white rice",
    "rod": "a fishing rod: a long pole with a line and a hook hanging at the end",
    "roll": "a single round golden-brown bread roll",
    "rope": "a neatly coiled brown rope",
    "saw": "a hand saw: a triangular metal blade with teeth and a wooden handle",
    "tag": "a paper price tag, tilted, with a short string through a hole at the top",
    "tape": "a roll of clear sticky tape on a round core, seen at an angle",
    "toast": "a single slice of browned toast with a yellow pat of butter on top",
    "vine": "a curling green vine with leaves and a bunch of purple grapes",
    "wig": "a curly brown wig of hair shaped like a hairstyle",
}


def main() -> None:
    if not client.is_configured():
        sys.exit("DEEPSEEK_API_KEY not set.")
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    made, failed = [], []
    for word, brief in BRIEFS.items():
        try:
            svg = svg_art.generate_svg(word, hint=brief)
            (IMG_DIR / f"{word}.svg").write_text(svg, encoding="utf-8")
            made.append(word)
            print(f"  ok   {word}")
        except (client.AgentError, ValueError) as exc:
            failed.append(word)
            print(f"  FAIL {word}: {exc}")

    # single review page of exactly this set
    OUT.mkdir(parents=True, exist_ok=True)
    cells = "".join(
        f'<div class=c><div class=b><img src="/static/img/words/{w}.svg"></div><div class=l>{w}</div></div>'
        for w in made
    )
    html = f"""<!doctype html><meta charset=utf-8><style>
body{{background:#FBF4EC;font-family:sans-serif;margin:0;padding:16px}}
.h{{text-align:center;color:#3A2E38;font-weight:700;margin:4px 0 12px}}
.grid{{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;max-width:1180px;margin:auto}}
.c{{background:#FFFDF8;border:2px solid #F6D8B8;border-radius:14px;padding:8px;text-align:center}}
.b{{height:84px;display:flex;align-items:center;justify-content:center}}
.b img{{width:80px;height:80px}} .l{{font-size:16px;color:#3A2E38;font-weight:600;margin-top:4px}}
</style><div class=h>regen pass — {len(made)} words</div><div class=grid>{cells}</div>"""
    (OUT / "regen.html").write_text(html)
    print(f"\n{len(made)} drawn, {len(failed)} failed -> static/_review/regen.html")


if __name__ == "__main__":
    main()
