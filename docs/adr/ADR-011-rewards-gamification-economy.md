# ADR-011 — Rewards & gamification economy

**Status:** Accepted *(2026-07-07; frozen before B9. The monotonic-non-decreasing invariant is permanent (invariant #3); the level curve / star values / freeze rules stay tunable in `engine/config.py` — tuning only ever makes rewards more generous, never retroactively removes.)*
**Date:** 2026-07-07 · **Related:** ADR-006 (`rewards.json`), ADR-007 (mastery→hatching), invariant #3, `PLAN.md` §6, `DESIGN_BRIEF.md` §4

## Context
The gamification is load-bearing motivation for a kid who "likes to be first" — but it's bound by invariant #3 (never subtract earned rewards, nothing punitive) and by the ADHD design rules (guaranteed early wins, end on a high, no shame on a bad day). The economy's *numbers* (star values, level thresholds, hatch condition, streak rules) are hard to change once she has progress — regressing someone's level is exactly the un-fun, trust-breaking move we must never make. So the curve is a decision of consequence, frozen once, tuned only upward.

## Decision

**Stars (the per-item currency):** correct-first-try = ⭐⭐ (2); correct-after-correction = ⭐ (1) — a corrected answer *always* still earns, never zero (DESIGN_BRIEF §5). Games (`bd_ninja`, `beat_yesterday`) award stars by performance, never negative. **Stars are only ever added** (invariant #3).

**XP & levels:** `xp = stars_total` (simple, legible to a 7-year-old: stars *are* progress). Levels use a gently rising curve `xp_for_level(n) = 20 · (n−1) · n / 2` — cumulative XP to reach level n — giving thresholds L1=0, L2=20, L3=60, L4=120, L5=200 (each level costs 20 more than the last), so early levels come fast (ADHD momentum) and later ones feel earned. Named tiers from `PLAN.md` §6 (Word Sprout 🌱 → … → Word Wizard 🧙). **Level never decreases** even if the model's mastery decays — XP is a record of effort spent, not current skill (that's what the rose of winds is for). This separation is deliberate: skill can fade and come back; her trophies do not.

**Creature collection:** each skill that reaches "mastered" (ADR-007: ≥ 85 over ≥ 2 sessions) hatches its bound creature (`collection[]` in `rewards.json`, one creature per skill). If mastery later decays below 85, **the creature stays hatched** (invariant #3) — the shelf is a permanent record of "you did this once".

**Streak:** +1 per calendar day with a finished session; `last_day` tracks it. **Freeze tokens**: earn 1 per 5-day streak (max 2 held); a missed day auto-spends a freeze to preserve the flame (DESIGN_BRIEF §1 rationale — losing a long streak is devastating for an ADHD kid). No freeze → the streak resets to 0 quietly (never a "you failed" screen; the next session just starts a new streak warmly).

**Reward moments** are pure presentation over this data (ADR-010): session chest (§4), level-up celebration (§4b), creature hatch (§4c) — the engine flags which fired; the UI animates.

All constants (star values, level curve, hatch threshold, freeze rules) live in `engine/config.py` alongside the ADR-007 constants — tunable in one place, but **the invariant is that tuning only ever makes rewards more generous or slower to lose, never retroactively takes something away.**

## Alternatives rejected
- **XP decoupled from stars (separate scoring)** — more designer control, but a second opaque currency confuses a 7-year-old; "stars = progress" is legible and honest.
- **Level tied to current mastery** — tempting (level = skill), but then decay would *demote* her, which is punitive and breaks invariant #3 and her trust. Effort-based XP that only rises is the therapeutic choice.
- **Losing streaks hard (no freeze)** — "authentic" but cruel for this user; the freeze token is a deliberate, evidence-based accommodation.
- **Leaderboards / compare-to-others** — explicitly excluded (DESIGN_BRIEF §10); she competes only with her own record (`beat_yesterday`), the safe form of "being first".

## Consequences
- **Makes easy:** every reward surface is a pure function of `rewards.json`; motivation tuned in one config block; a provably-non-punitive system (invariant #3 is a testable property: rewards are monotonic non-decreasing).
- **Makes hard / costs:** the level curve is a guess until she plays — but it only tunes upward, so there's no trust cost to adjusting.
- **Follow-ups:** a guardrail test asserting rewards never decrease across any operation; the skill→creature binding table authored with the word banks/art.
- **Risks accepted:** she might "grind" easy games for stars — fine; the mastery model (separate) still tells the parent the truth about skill, and grinding easy wins is still time-on-task.
