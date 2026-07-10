"""Tunable constants for the deterministic engine.

ONE place for the pedagogy numbers (ADR-007) and reward economy (ADR-011), so
tuning the child's experience is a single-file change with a test — never a hunt.
Changing a value here is expected and does NOT need a new ADR; the ADRs freeze the
*rules*, this file holds the *knobs*.
"""

# ---- The 14 skills (PLAN.md §2 / ADR-006). Order = the teaching sequence. ----
# id -> per-day mastery decay (ADR-007 rule 3): heart words fade fastest (pure
# memory), rule-based skills slowest, foundation/composition in between.
SKILLS: dict[str, float] = {
    # Strand A — letters & sounds
    "letter_orientation": 0.8,
    "phoneme_segmentation": 0.8,
    "short_vowels": 0.6,
    "blends": 0.5,
    # Strand B — patterns & rules
    "digraphs": 0.5,
    "magic_e": 0.5,
    "vowel_teams": 0.5,
    "r_controlled": 0.5,
    "doubling_endings": 0.5,
    # Strand C — words
    "heart_words": 1.2,
    "suffixes": 0.5,
    # Strand D — composition
    "word_sequencing": 0.8,
    "phrase_dictation": 0.8,
    "sentence_writing": 0.8,
}
SKILL_IDS: tuple[str, ...] = tuple(SKILLS)

# ---- Mastery model (ADR-007) ----
INITIAL_MASTERY = 20          # a newly *introduced* skill starts here, not at 0
EMA_K_BASE = 0.4              # learning rate at exposure 0
EMA_K_MIN = 0.12             # floor so late results still move a little
EMA_K_HALFLIFE = 8.0         # exposures scale in K = max(K_MIN, K_BASE/(1+exp/HL))
SCORE_FIRST_TRY = 1.0
SCORE_AFTER_CORRECTION = 0.5
SCORE_MISS = 0.0
UNLOCK_THRESHOLD = 60         # prereqs must reach this (effective, at session end)
MASTERY_THRESHOLD = 85        # "mastered" → hatches a creature (ADR-011)
WARMUP_MASTERY = 75           # warm-up / closing items drawn from skills ≥ this

# ---- Selection mix (ADR-007 rule 5) ----
ITEMS_PER_SESSION = 10
MIX_FOCUS = 0.6
MIX_REVIEW = 0.3
MIX_STRETCH = 0.1
WARMUP_ITEMS = 2              # first N items are guaranteed early wins

# ---- Scaffold ladder (ADR-007 rule 5 / ADR-005 scaffold_level) ----
# Kept for scaffold_level numbering + step-down: MOST-scaffold → LEAST.
SCAFFOLD_TYPES = ("word_builder", "letter_boxes", "echo_dictation")
# effective-mastery band cutoffs: <45 low · 45–75 mid · ≥75 high (~80% success).
SCAFFOLD_CUTOFFS = (45, 75)

# ---- Exercise-type policy (ADR-014) ----
# Per mastery band, the ROTATION of allowed exercise types (variety within a
# session instead of one type repeated). Skill-specific overrides below.
TYPE_BANDS = {
    "low": ("word_builder", "letter_boxes"),
    "mid": ("letter_boxes", "missing_letters", "word_sort"),
    "high": ("echo_dictation", "missing_letters"),
}
TYPE_OVERRIDES = {
    # skill_id -> {band: rotation}. Omitted bands fall back to TYPE_BANDS.
    "heart_words": {
        "low": ("word_builder", "heart_word_spotlight"),
        "mid": ("heart_word_spotlight", "letter_boxes"),
        "high": ("heart_word_spotlight", "echo_dictation"),
    },
    "letter_orientation": {  # her b/d reversal → the discrimination game
        "low": ("bd_ninja",), "mid": ("bd_ninja",), "high": ("bd_ninja",),
    },
    "phoneme_segmentation": {  # sound boxes ARE segmentation practice
        "low": ("word_builder", "letter_boxes"), "mid": ("word_builder", "letter_boxes"),
        "high": ("letter_boxes", "missing_letters"),
    },
    "word_sequencing": {  # long words; holding the sequence is the point
        "low": ("letter_boxes", "word_builder"), "mid": ("letter_boxes", "echo_dictation"),
        "high": ("echo_dictation", "letter_boxes"),
    },
    "phrase_dictation": {
        "low": ("phrase_dictation",), "mid": ("phrase_dictation",), "high": ("phrase_dictation",),
    },
    "sentence_writing": {
        "low": ("sentence_scribe",), "mid": ("sentence_scribe",), "high": ("sentence_scribe",),
    },
}
# Strand-D & no-bank skills source their content from OTHER banks (ADR-014 §3):
CONTENT_FROM_OTHER_BANKS = (
    "letter_orientation", "phoneme_segmentation", "word_sequencing",
    "phrase_dictation", "sentence_writing",
)
LONG_WORD_MIN_DIFFICULTY = 4   # word_sequencing draws these
CHALLENGE_ITEMS = 1            # PLAN §7 step 5 (skippable, only when unlocked)
FOCUS_EXCLUDED = ("letter_orientation",)  # a mini-game can't be the lesson focus
GAME_ITEMS_MAX = 1             # at most one bd_ninja round per session (variety)
BD_NINJA_LETTERS = 16          # letters per b/d round
BD_NINJA_PASS = 0.8            # lenient game threshold (ADR-014 §4)

# ---- Reward economy (ADR-011) — ONLY ever added to (invariant #3) ----
STARS_FIRST_TRY = 2
STARS_AFTER_CORRECTION = 1
LEVEL_NAMES = (
    "Word Sprout", "Word Scout", "Word Ranger", "Word Champion", "Word Wizard",
)


def k_for_exposures(exposures: int) -> float:
    """EMA learning rate that slows as a skill accrues exposures (ADR-007 rule 2)."""
    return max(EMA_K_MIN, EMA_K_BASE / (1.0 + exposures / EMA_K_HALFLIFE))


def xp_for_level(n: int) -> int:
    """Cumulative XP needed to be AT level n (ADR-011): 20·(n-1)·n/2.

    L1=0, L2=20, L3=60, L4=120, … — early levels come fast (ADHD momentum),
    later ones are earned.
    """
    n = max(1, n)
    return 20 * (n - 1) * n // 2


def level_for_xp(xp: int) -> int:
    """Highest level whose XP threshold is met. Level never decreases (ADR-011)."""
    level = 1
    while xp >= xp_for_level(level + 1):
        level += 1
    return level


def level_name(level: int) -> str:
    return LEVEL_NAMES[min(level, len(LEVEL_NAMES)) - 1]
