# ADR-008 — Error classifier: alignment algorithm + tag taxonomy

**Status:** Accepted *(2026-07-07; pedagogy-critical. The tag ENUM is frozen (renames forbidden; additions allowed); detection thresholds remain tunable. Owner may revise tag semantics via a superseding ADR if real error data warrants.)*
**Date:** 2026-07-07 · **Related:** ADR-007 (tags drive mastery), ADR-006 (tags stored in session logs), `PLAN.md` §4

## Context
Every wrong spelling must become a *signal*, not just a "wrong". The classifier compares `attempt` vs `target`, tags the error type(s), and those tags (a) drive which skill's mastery moves (ADR-007), (b) are stored in session logs forever (ADR-006), (c) feed the agent's explanation and the parent error log. The tag *taxonomy* is therefore a permanent data contract — renaming a tag later orphans historical logs. It must be deterministic and free (no AI) so it's fast and always available (ADR-002 fallback).

## Decision

**Alignment:** compute a character-level alignment via **Levenshtein with backtrace** (Needleman–Wunsch-style edit script) to label each position as match / substitution / insertion / deletion, plus a transposition check (adjacent swap). Pure Python, ~40 lines, no dependency. Phoneme-aware refinement: align against the word bank entry's `phonemes` too, so `luv`/`love` reads as "phonetically plausible" rather than "3 substitutions".

**The FROZEN tag taxonomy** (from `PLAN.md` §4; adding a tag later is allowed, renaming is not):
| tag | detection | primary skill hit |
|-----|-----------|-------------------|
| `reversal` | a letter replaced by its mirror (b↔d, p↔q, m↔w) | `letter_orientation` |
| `transposition` | two adjacent letters swapped | `word_sequencing` |
| `omission` | a target letter missing | `word_sequencing` / `phoneme_segmentation` |
| `insertion` | an extra letter added | `phoneme_segmentation` |
| `phonetic_plausible` | attempt is a valid phonetic spelling of the target | the target word's `pattern` skill |
| `vowel_substitution` | wrong vowel, right consonant frame | `short_vowels` / `vowel_teams` |
| `pattern_violation` | breaks the target's orthographic rule (luvv, chik) | `doubling_endings` / `digraphs` |
| `heart_word_miss` | miss on a word flagged irregular | `heart_words` |
| `correct` | exact match (after grading normalization) | — |

- **Multiple tags allowed** per attempt (e.g. `reversal` + `omission`); mastery updates apply to each tagged skill, weighted (primary tag full, secondary half).
- **Precedence:** heart-word targets check `heart_word_miss` first; `phonetic_plausible` outranks raw substitution tags (it's the more informative signal — it's *why* `luv` happens).
- Classifier output: `{ tags:[...], primary_skill, alignment:[...], is_phonetic:bool }`. The `alignment` feeds the ADR-005 `reveal.markers` so the correction screen highlights exactly the wrong part.

## Alternatives rejected
- **Plain string equality (right/wrong only)** — throws away the entire diagnostic signal that makes this app more than a quiz; the rose of winds would have nothing to point at.
- **LLM-based classification** — the agent *could* tag errors, but that's non-deterministic, costs a call per answer, and can't run offline; worse, it's unauditable for a pedagogy-critical signal. The agent instead *explains* the deterministic tag in kid language (ADR-012). Fallback: the agent may add a free-text "note" the classifier can't express (e.g. a cross-word pattern), stored alongside, never replacing, the tags.
- **Full phonetic engine (grapheme-to-phoneme ML)** — overkill; a curated `phonemes` field per word bank entry (ADR-006) gives us phonetic-plausibility checks without a dependency.

## Consequences
- **Makes easy:** deterministic, testable, free error signals; a stable taxonomy the parent dashboard and agent both speak; marker-driven correction highlights for free.
- **Makes hard / costs:** phonetic-plausibility depends on good `phonemes`/`distractors` data per word — content work, tracked with the word banks.
- **Follow-ups:** the alignment + each tag detector is a prime cross-authored test target (edge cases: `dehind`, `freind`, `luv`, `sed`); freeze the tag enum in `engine/classifier.py` with a test asserting no tag renames.
- **Risks accepted:** rare mis-tags (a swap that's also a plausible spelling) — precedence rules pick the most useful tag; the parent log shows the raw attempt so a human can always see the truth.
