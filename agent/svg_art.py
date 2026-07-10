"""Generate simple, kid-friendly word-picture SVGs with DeepSeek (owner idea
2026-07-10). The lead reviews the word, briefs the model, the model returns SVG
CODE, and the lead renders + eyeballs it before it's saved (a wrong/crude picture
is worse than none — same bar as the emoji audit).

Security: LLM-authored SVG is untrusted. `sanitize_svg` strips scripts, event
handlers, external references and foreignObject so the file is safe to serve as a
static <img> (returns None if it can't be made safe or isn't a real SVG).
No LETTERS may appear — a spelling picture must never show the word's spelling.
"""
from __future__ import annotations

import re

from . import client

VIEWBOX = "0 0 120 120"

_SYSTEM = (
    "You are an illustrator making tiny, ultra-simple picture icons for a "
    "spelling game for a 6-year-old with dyslexia. Draw ONE clear, friendly, "
    "instantly-recognizable object with bold simple shapes and a few solid "
    "colors — like a children's flash card. Center it in a "
    f"{VIEWBOX} viewBox. Rules: absolutely NO text, letters, numbers or words "
    "anywhere in the image; no gradients; no <script>, <foreignObject>, external "
    "links or images; keep it under ~1500 characters. Return ONLY the raw "
    "<svg>...</svg> markup — no markdown fences, no commentary."
)

# unsafe constructs → the SVG is rejected/scrubbed
_SCRIPT_RE = re.compile(r"<script\b.*?</script\s*>", re.IGNORECASE | re.DOTALL)
_FOREIGN_RE = re.compile(r"<foreignObject\b.*?</foreignObject\s*>", re.IGNORECASE | re.DOTALL)
_ON_ATTR_RE = re.compile(r"\son\w+\s*=\s*(\"[^\"]*\"|'[^']*'|\S+)", re.IGNORECASE)
_EXTERNAL_RE = re.compile(r"(href|xlink:href|src)\s*=\s*(\"|')\s*(https?:|//|data:text/html)", re.IGNORECASE)
_TEXT_RE = re.compile(r"<text\b|<tspan\b", re.IGNORECASE)


def default_brief(word: str, hint: str = "") -> str:
    what = f"a {word}" + (f" ({hint})" if hint else "")
    return f"Draw {what}."


def sanitize_svg(svg: str) -> str | None:
    """Return a safe-to-serve SVG string, or None if it can't be trusted / isn't a
    real single SVG / contains letters (which would leak the spelling)."""
    if not svg:
        return None
    start = svg.find("<svg")
    end = svg.rfind("</svg>")
    if start < 0 or end < 0:
        return None
    svg = svg[start : end + len("</svg>")]
    svg = _SCRIPT_RE.sub("", svg)
    svg = _FOREIGN_RE.sub("", svg)
    svg = _ON_ATTR_RE.sub("", svg)
    if _EXTERNAL_RE.search(svg) or "javascript:" in svg.lower():
        return None
    if _TEXT_RE.search(svg):  # a spelling picture must never contain letters
        return None
    if len(svg) > 6000 or "viewBox" not in svg and "viewbox" not in svg:
        return None
    return svg.strip()


_CLASSIFY_SYSTEM = (
    "For each word, decide if it names something a 6-year-old could INSTANTLY "
    "recognize as one simple picture. YES: concrete objects, animals, food, and "
    "clearly-depictable actions (jump, dig, run, hug). NO: abstract or relational "
    "or function words (the, was, from, plan, come, only, very), and anything that "
    "would look like a DIFFERENT word as a picture. For each YES give a one-line "
    "visual description of the single clearest way to draw it. Return ONLY a JSON "
    "array: [{\"word\":..,\"drawable\":true/false,\"draw\":\"<desc or empty>\"}]. No prose."
)


def classify_words(words: list[str], *, timeout: float = 40.0) -> dict[str, dict]:
    """{word: {"drawable": bool, "draw": brief}} for a batch. Unparseable rows and
    unknown words dropped; raises AgentError on transport failure."""
    import json
    import re

    lines = "\n".join(words)
    resp = client.chat(
        [
            {"role": "system", "content": _CLASSIFY_SYSTEM},
            {"role": "user", "content": "Words:\n" + lines},
        ],
        timeout=timeout,
        temperature=0.1,
        max_tokens=2000,
    )
    content = client.first_message(resp).get("content", "")
    match = re.search(r"\[.*\]", content, re.DOTALL)
    if not match:
        return {}
    try:
        rows = json.loads(match.group(0))
    except (ValueError, TypeError):
        return {}
    want = {w.lower() for w in words}
    out: dict[str, dict] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        w = str(row.get("word", "")).strip().lower()
        if w in want:
            out[w] = {"drawable": bool(row.get("drawable")), "draw": str(row.get("draw") or "").strip()}
    return out


def generate_svg(word: str, *, hint: str = "", timeout: float = 40.0) -> str:
    """Ask the model for a word icon; return sanitized SVG. Raises AgentError on
    transport failure or ValueError if the result can't be made safe."""
    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": default_brief(word, hint)},
    ]
    resp = client.chat(messages, timeout=timeout, temperature=0.4, max_tokens=1600)
    raw = client.first_message(resp).get("content", "")
    safe = sanitize_svg(raw)
    if not safe:
        raise ValueError(f"unusable SVG for {word!r}")
    return safe
