# ADR-007 — Mastery model & adaptive selection algorithm

**Status:** Proposed *(PEDAGOGY-CRITICAL — owner sign-off + a second-ideator pass before locking)*
**Date:** 2026-07-07 · **Related:** ADR-006 (skill record), ADR-008 (tags feed this), `PLAN.md` §1/§2

## Context
This is the brain: it decides how a result moves a skill's mastery, how mastery fades, when a skill unlocks, and what she practices next. `PLAN.md` §2 fixes the shape (0–100 mastery, decay, prerequisite gates, 60/30/10 selection, step-down); this ADR fixes the *numbers and formulas* so the engine is deterministic and its stored history has stable meaning. Pedagogy-critical because the numbers encode the ~80%-success and spiral-review principles from §1 — get them wrong and she's either bored or defeated.

## Decision (deterministic; the agent may re-order within a plan but not change these rules)

**1. Grading a result → a score.** Per graded attempt: correct-first-try = 1.0; correct-after-correction = 0.5; miss (even after retype) = 0.0. (The retype-right step teaches; it doesn't count as first-try mastery.)

**2. Mastery update (EMA with a slowing learning rate):**
`mastery ← clamp(mastery + K · (100·score − mastery), 0, 100)`
where `K = max(0.12, 0.4 / (1 + exposures/8))` — early exposures move fast, later ones stabilize (prevents one bad day from wiping a solid skill). `exposures`, `streak`, `last_practiced` updated each attempt.

**3. Decay (forces spiral review — the core dyslexia principle):** on load, for each skill, apply `mastery ← max(0, mastery − decay_per_day · days_since_practiced)`. Default `decay_per_day = 0.8`; heart words decay faster (1.2, pure memory), rule-based skills slower (0.5). Decay is applied lazily at read time (no cron needed — fits the file store).

**4. Prerequisite gates (introduce, never overwhelm):** a skill is `introduced` only when all its prerequisites are ≥ 60. Prereq map lives in `data/word_bank/skill_graph.json` (e.g. `magic_e ← short_vowels`; `vowel_teams ← short_vowels, digraphs`). A skill is "mastered" (hatches its creature, ADR-011) at ≥ 85 sustained over ≥ 2 sessions.

**5. Selection per session (the 60/30/10, made concrete):** target `items_per_session` (default 10):
- **60% focus:** the lowest-mastery *introduced* skill = the session's focus pattern (drives the teach card).
- **30% spiral review:** skills ranked by `decay_drop` (how much decay pulled them down) × recency — refresh what's fading.
- **10% stretch:** one item from the next *not-yet-introduced* skill whose prereqs just cleared (a teaser), OR an extra review item if none qualifies.
- **Warm-up override:** the first 2 items are always from skills with mastery ≥ 75 (guaranteed early wins, §1 / ADR-011).
- **~80% success targeting:** the selector picks the *scaffold level* (ADR-005 `scaffold_level`, mapped to exercise type per §3's ladder) to aim ~80% correct for the current mastery — low mastery → high-scaffold types (`word_builder`), high mastery → low-scaffold (`echo_dictation`).

**6. Step-down (never spiral into failure):** two consecutive misses → the same target is re-served one scaffold level easier; the session is guaranteed to end on a success item (reorder so a ≥75-mastery item is last).

All constants live in one `engine/config.py` block so tuning them is a one-file change with a test, not a hunt.

## Alternatives rejected
- **Full SRS (SM-2 / Anki intervals)** — proven for flashcards, but it schedules *whole cards by date*; we need *skill-level* mastery driving *exercise-type* selection and ~80% difficulty targeting. SM-2's ease-factor model doesn't express "pick an easier exercise type." We borrow its spaced-review spirit via decay. Fallback: if decay-based review proves too crude, layer per-word SRS *under* the skill model later.
- **Simple % correct as mastery** — no recency weighting, so a skill looks mastered forever on old wins; EMA + decay is what makes the rose of winds tell the truth.
- **Let the agent compute mastery** — non-deterministic, unauditable, and breaks the offline-fallback guarantee (ADR-002). The math stays deterministic; the agent only adds narrative/ordering.

## Consequences
- **Makes easy:** an auditable, testable brain (pure functions over the skill record); tuning via one config block; the parent radar reflects real current ability.
- **Makes hard / costs:** the constants need real-world tuning once she uses it — expected; they're isolated for exactly that.
- **Follow-ups:** `skill_graph.json` (prereqs) authored with the word banks; a rich unit-test suite (this is the highest-value test target); the scaffold-level→exercise-type map formalized with ADR-005.
- **Risks accepted:** the initial constants are educated guesses; the design (isolated config + decay observability in the parent dashboard) makes correcting them cheap.
