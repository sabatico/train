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
# Exercise types ordered MOST-scaffold → LEAST. Phase-1 ships these three; more
# slot in later without changing the mapping shape. Index+1 = scaffold_level.
SCAFFOLD_TYPES = ("word_builder", "letter_boxes", "echo_dictation")
# effective-mastery cutoffs between the ladder rungs (len = len(SCAFFOLD_TYPES)-1):
# <45 → most scaffold (word_builder); 45–75 → letter_boxes; ≥75 → echo_dictation.
# Targets ~80% success — a shakier skill gets a more forgiving exercise.
SCAFFOLD_CUTOFFS = (45, 75)

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
