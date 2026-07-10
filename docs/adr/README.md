# ADR Log — Spell Quest

The running list of **locked architectural decisions.** Read this before making a decision of consequence — the answer may already be here. **Never re-litigate a locked (Accepted) ADR;** to change one, write a new ADR that supersedes it. Process: `../sops/decisions-adr.md`.

| # | Title | Status | Date |
|---|-------|--------|------|
| [ADR-001](ADR-001-flask-file-json-store.md) | Python/Flask backend with a file-based JSON store | Accepted | 2026-07-07 |
| [ADR-002](ADR-002-deepseek-teacher-agent.md) | DeepSeek API as the teacher-agent LLM, with a mandatory deterministic fallback | Accepted | 2026-07-07 |
| [ADR-003](ADR-003-ui-stack-tokens-vanilla.md) | UI stack: token CSS + scoped CSS + vanilla-JS component registry (no framework) | Accepted | 2026-07-07 |
| [ADR-004](ADR-004-single-user-first-scale-seams.md) | Build v1 single-user, keep four named seams clean for the Stage-2 multi-user service | Accepted | 2026-07-07 |
| [ADR-005](ADR-005-exercise-interaction-contract.md) | The exercise/interaction JSON contract (one seam, three consumers) | Accepted | 2026-07-07 |
| [ADR-006](ADR-006-data-model-file-store-schema.md) | Data model & file-store schema (records, IDs, on-disk layout) | Accepted | 2026-07-07 |
| [ADR-007](ADR-007-mastery-and-selection-algorithm.md) | Mastery model & adaptive selection algorithm | Accepted | 2026-07-07 |
| [ADR-008](ADR-008-error-classifier-alignment-taxonomy.md) | Error classifier: alignment + tag taxonomy | Accepted | 2026-07-07 |
| [ADR-009](ADR-009-session-lifecycle-state.md) | Session lifecycle & where in-flight state lives | Accepted | 2026-07-07 |
| [ADR-010](ADR-010-frontend-app-architecture.md) | Frontend app architecture (SPA shell, registry, router, audio wrapper) | Accepted | 2026-07-07 |
| [ADR-011](ADR-011-rewards-gamification-economy.md) | Rewards & gamification economy | Accepted | 2026-07-07 |
| [ADR-012](ADR-012-agent-integration-contract.md) | Agent integration contract (tool-use, PII boundary, caching, fallback) | Accepted | 2026-07-07 |
| [ADR-013](ADR-013-openai-tts-pregenerated-audio.md) | OpenAI TTS as the pre-generated dictation-audio provider | Accepted | 2026-07-08 |
| [ADR-014](ADR-014-session-experience-redesign.md) | Session-experience redesign: the full learning path, as designed | Accepted | 2026-07-09 |

> Number monotonically; never reuse. One file per ADR: `ADR-NNN-short-slug.md`.

## Stage-1 ADR roadmap — ALL ACCEPTED 2026-07-07
ADRs 005–012 are the "lowered-altitude" build contracts derived from `PLAN.md`, all scoped to **Stage 1 / single-user**, accepted on the owner's "proceed". Pedagogy-critical ones carry tunable constants (in `engine/config.py`) so the owner can adjust the child's experience without a new ADR; the frozen parts are noted in each status line. ADR-007 had an inline second-ideator pass that fixed a compounding-decay bug and a premature-unlock hole before acceptance.

Build items in `runner.md` §B may now proceed against their governing ADR.
