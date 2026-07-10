# ADR-014 — Session-experience redesign: the full learning path, as designed

**Status:** Accepted *(owner mandate 2026-07-09: "present functionality path has no sense — re-review all functionality and redo in full")*
**Date:** 2026-07-09 · **Related:** PLAN §3/§7, DESIGN_BRIEF §6, ADR-005/007/012; supersedes the scaffold-ladder *interpretation* in ADR-007 rule 5 (the 60/30/10 mix itself stands)

## Context
The owner's product review found the shipped experience fails the design: sessions are ~90% one exercise type (mastery→single-type mapping = monotone tile-tapping daily); the words→phrases→sentences progression — the core of the product vision — is unreachable (Strand D skills have no content source and no exercises); `letter_orientation` (the child's signature b/d reversal) is an unreachable skill; heart words are served like decodable words (pedagogically wrong); the agent never reads its memory or reviews writing; earned gamification is invisible to the child. The engine/corpus/contract foundations are sound — the assembly on top is what's wrong.

## Decision
1. **Session shape per PLAN §7, faithfully:** warmup(2 easy wins) → teach → practice(6, focus+review, **rotating** exercise types) → **challenge(0–1: phrase/sentence dictation when unlocked, skippable)** → reward.
2. **Slot- and skill-aware exercise policy with rotation** (replaces mastery→one-type): per mastery band a *set* of allowed types, rotated per item — low: [word_builder, letter_boxes]; mid: [letter_boxes, missing_letters, word_sort]; high: [echo_dictation, missing_letters]. Skill overrides: `heart_words`→heart_word_spotlight (+word_builder low / echo high); `letter_orientation`→bd_ninja; `phoneme_segmentation`→word_builder (sound boxes ARE segmentation) on other banks' words; `word_sequencing`→letter_boxes/echo on LONG words (difficulty ≥4); `phrase_dictation`→phrase_dictation; `sentence_writing`→sentence_scribe. **Every one of the 14 skills is now reachable.**
3. **Strand D content from the enriched corpus:** phrase/sentence items take their target from the word banks' AI-enriched `phrase`/`sentence` fields of introduced-skill words (no separate banks needed). Grading is word-by-word, case- and end-punctuation-forgiving (never punitive); the correction routine reuses the existing reveal→retype flow with the full phrase/sentence.
4. **All ten PLAN §3 exercise types implemented** (payload builders + validators in contracts, renderers in the registry): + missing_letters, word_sort, heart_word_spotlight, phrase_dictation, sentence_scribe, bd_ninja. (beat_yesterday = the opt-in game, backlog T-013.) bd_ninja is client-scored ("hits/misses" attempt, server applies a lenient threshold) — an accepted exception to server-authoritative grading for the timed game.
5. **Agent as teacher, per ADR-012:** reviews `sentence_scribe` writing (praise-first, ≤2 corrections, each with a why; deterministic diff+why_for fallback), and its prompts now include the recent teacher-notebook (memory.md) tail. (Full session planning stays T-012.)
6. **Gamification made visible (DESIGN_BRIEF §1/§4/§5):** home shows streak flame, level badge, today's mission; reward screen shows level progress + level-up + hatch moments; a collection shelf screen. Served by a new `GET /api/home`.

## Alternatives rejected
- **Patch the type ladder only** — doesn't restore the missing progression (phrases/sentences) or dead skills; the monotony was a symptom, not the disease.
- **Separate phrase/sentence banks** — the 707 AI-enriched phrases/sentences already exist per word; a second content pipeline would duplicate it.
- **Agent-planned sessions now** (full ADR-012 site #1) — bigger surface, nondeterministic; the deterministic redesign restores the experience first; enrichment remains T-012.

## Consequences
- **Makes easy:** the designed daily arc (variety, progression, her b/d game, visible rewards); every skill practicable; writing reviewed with the "why".
- **Makes hard / costs:** selector/session substantially rewritten + 6 new renderers + new tests; bd_ninja grading exception documented.
- **Follow-ups:** beat_yesterday game (T-013), agent session planning (T-012), phonically-accurate sound display (/k/ for c) — backlog.
