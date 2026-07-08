"""Error classifier — turns a wrong spelling into skill signals (ADR-008).

Deterministic, dependency-free, and free to run (no AI), so it always works and
is fast (ADR-002 fallback). Compares `attempt` vs `target` with a Levenshtein
alignment, then tags the error(s) from the FROZEN taxonomy. Tags drive mastery
(ADR-007), are stored forever (ADR-006), and feed the agent's kid-voice
explanation (ADR-012). The tag ENUM must not be renamed (only extended).
"""
from __future__ import annotations

# The frozen tag set (ADR-008). Renaming any of these breaks historical logs.
TAGS = (
    "correct",
    "reversal",
    "transposition",
    "omission",
    "insertion",
    "phonetic_plausible",
    "vowel_substitution",
    "pattern_violation",
    "heart_word_miss",
)

_MIRRORS = {"b": "d", "d": "b", "p": "q", "q": "p", "m": "w", "w": "m"}
_VOWELS = set("aeiou")


# --------------------------------------------------------------- alignment
def align(attempt: str, target: str) -> list[tuple[str, str, str]]:
    """Levenshtein alignment with backtrace. Returns a list of ops:
    ("match"|"sub"|"del"|"ins", attempt_char, target_char) reading left→right.
    'del' = a target char missing from the attempt (omission); 'ins' = an extra
    attempt char (insertion)."""
    a, b = attempt, target
    n, m = len(a), len(b)
    # cost matrix
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        d[i][0] = i
    for j in range(1, m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
    # backtrace (prefer diagonal on ties for stable, readable alignments)
    ops: list[tuple[str, str, str]] = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and d[i][j] == d[i - 1][j - 1] + (0 if a[i - 1] == b[j - 1] else 1):
            ops.append(("match" if a[i - 1] == b[j - 1] else "sub", a[i - 1], b[j - 1]))
            i, j = i - 1, j - 1
        elif i > 0 and d[i][j] == d[i - 1][j] + 1:
            ops.append(("ins", a[i - 1], ""))   # extra attempt char
            i -= 1
        else:
            ops.append(("del", "", b[j - 1]))   # missing target char
            j -= 1
    ops.reverse()
    return ops


def _is_transposition(attempt: str, target: str) -> bool:
    """True if the attempt is the target with exactly one adjacent pair swapped
    (freind/friend)."""
    if len(attempt) != len(target) or attempt == target:
        return False
    diffs = [k for k in range(len(target)) if attempt[k] != target[k]]
    return (
        len(diffs) == 2
        and diffs[1] == diffs[0] + 1
        and attempt[diffs[0]] == target[diffs[1]]
        and attempt[diffs[1]] == target[diffs[0]]
    )


# --------------------------------------------------------------- phonetics
def _phonetic_key(word: str) -> str:
    """A rough phonetic normalization so phonetically-equivalent spellings collide
    (luv↔love, sed↔said, fone↔phone). Deliberately conservative — it recognises the
    common patterns a 7-year-old produces, not a full G2P engine (ADR-008: the
    curated word bank carries phonemes; this is the free heuristic layer)."""
    w = word.lower()
    # multi-char graphemes → canonical sound
    for a, b in (
        ("ph", "f"), ("gh", "f"), ("ck", "k"), ("qu", "kw"),
        ("igh", "i"), ("ai", "a"), ("ay", "a"), ("ea", "e"), ("ee", "e"),
        ("oa", "o"), ("ow", "o"), ("ou", "o"), ("oo", "u"),
        ("ce", "se"), ("ci", "si"),
    ):
        w = w.replace(a, b)
    # drop a trailing silent e (love→lov, hope→hop-ish)
    if len(w) > 2 and w.endswith("e") and w[-2] not in _VOWELS:
        w = w[:-1]
    out = []
    for ch in w:
        if ch == "c":
            ch = "k"          # hard c → k (cat→kat)
        if ch == "y":
            ch = "i"
        if out and out[-1] == ch:
            continue          # collapse doubles (buzz→buz)
        out.append(ch)
    return "".join(out)


def is_phonetically_plausible(
    attempt: str, target: str, target_phonemes: list[str] | None = None
) -> bool:
    """Does the attempt spell a valid *sound* of the target?

    ADR-008: strongest when the target's curated `phonemes` are supplied (the
    word bank carries them) — e.g. love's phonemes are ['l','u','v'], so 'luv'
    matches even though the letter 'o' doesn't. Without phonemes we fall back to a
    spelling-based key, which is conservative and may miss irregular vowels."""
    a, t = attempt.strip().lower(), target.strip().lower()
    if a == t:
        return False  # exact match isn't an "error tag"
    key_a = _phonetic_key(a)
    if target_phonemes:
        if key_a == _phonetic_key("".join(target_phonemes).lower()):
            return True
    return key_a == _phonetic_key(t)


# --------------------------------------------------------------- classify
def classify(
    attempt: str,
    target: str,
    *,
    is_heart_word: bool = False,
    target_phonemes: list[str] | None = None,
) -> dict:
    """Classify one attempt against its target. Returns
    {tags, primary, alignment, is_phonetic} (ADR-008). Multiple tags may apply;
    `primary` is the most informative one for driving mastery/feedback. Pass the
    target's `phonemes` (from the word bank) for accurate phonetic detection."""
    a = (attempt or "").strip().lower()
    t = (target or "").strip().lower()
    ops = align(a, t)

    if a == t:
        return {"tags": ["correct"], "primary": "correct", "alignment": ops, "is_phonetic": False}

    tags: list[str] = []
    phonetic = is_phonetically_plausible(a, t, target_phonemes)

    # reversal: a substitution where attempt/target chars are mirror letters
    if any(op == "sub" and _MIRRORS.get(ac) == tc for op, ac, tc in ops):
        tags.append("reversal")
    # transposition (adjacent swap)
    if _is_transposition(a, t):
        tags.append("transposition")
    # omission / insertion from the alignment
    if any(op == "del" for op, _, _ in ops):
        tags.append("omission")
    if any(op == "ins" for op, _, _ in ops):
        tags.append("insertion")
    # vowel substitution: a sub where both chars are vowels (pit/pet)
    if any(op == "sub" and ac in _VOWELS and tc in _VOWELS for op, ac, tc in ops):
        tags.append("vowel_substitution")
    if phonetic:
        tags.append("phonetic_plausible")
    # heart-word miss on an irregular word
    if is_heart_word:
        tags.append("heart_word_miss")

    # a same-length all-substitution miss that isn't any of the above still needs a tag
    if not tags:
        tags.append("pattern_violation")

    primary = _primary_tag(tags, is_heart_word=is_heart_word)
    return {"tags": tags, "primary": primary, "alignment": ops, "is_phonetic": phonetic}


def _primary_tag(tags: list[str], *, is_heart_word: bool) -> str:
    """Precedence (ADR-008): heart-word miss dominates on irregular words; then
    phonetic-plausible (the most informative 'why'); then structural tags."""
    order = [
        "heart_word_miss" if is_heart_word else None,
        "phonetic_plausible",
        "reversal",
        "transposition",
        "vowel_substitution",
        "omission",
        "insertion",
        "pattern_violation",
    ]
    for tag in order:
        if tag and tag in tags:
            return tag
    return tags[0]  # pragma: no cover — classify() always seeds a known tag first
