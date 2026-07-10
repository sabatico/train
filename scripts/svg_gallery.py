"""Build paged verification galleries of the generated word SVGs for the lead's
visual pass. Writes static/_review/page-N.html (gitignored). Not product."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "static" / "img" / "words"
OUT = ROOT / "static" / "_review"
PER = 30
m = json.loads((ROOT / "data" / "word_images.json").read_text())
words = sorted(w for w, v in m.items() if v.get("status") == "ok" and (IMG / f"{w}.svg").exists())
OUT.mkdir(parents=True, exist_ok=True)
pages = [words[i:i+PER] for i in range(0, len(words), PER)]
for n, page in enumerate(pages, 1):
    cells = "".join(
        f'<div class=c><div class=b><img src="/static/img/words/{w}.svg"></div><div class=l>{w}</div></div>'
        for w in page
    )
    html = f"""<!doctype html><meta charset=utf-8><style>
body{{background:#FBF4EC;font-family:sans-serif;margin:0;padding:16px}}
.h{{text-align:center;color:#3A2E38;font-weight:700;margin:4px 0 12px}}
.grid{{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;max-width:1180px;margin:auto}}
.c{{background:#FFFDF8;border:2px solid #F6D8B8;border-radius:14px;padding:8px;text-align:center}}
.b{{height:84px;display:flex;align-items:center;justify-content:center}}
.b img{{width:80px;height:80px}} .l{{font-size:16px;color:#3A2E38;font-weight:600;margin-top:4px}}
</style><div class=h>page {n}/{len(pages)} — {len(page)} words</div><div class=grid>{cells}</div>"""
    (OUT / f"page-{n}.html").write_text(html)
print(f"{len(words)} art words across {len(pages)} pages written to static/_review/")
