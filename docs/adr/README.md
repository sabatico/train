# ADR Log — Spell Quest

The running list of **locked architectural decisions.** Read this before making a decision of consequence — the answer may already be here. **Never re-litigate a locked (Accepted) ADR;** to change one, write a new ADR that supersedes it. Process: `../sops/decisions-adr.md`.

| # | Title | Status | Date |
|---|-------|--------|------|
| [ADR-001](ADR-001-flask-file-json-store.md) | Python/Flask backend with a file-based JSON store | Accepted | 2026-07-07 |
| [ADR-002](ADR-002-deepseek-teacher-agent.md) | DeepSeek API as the teacher-agent LLM, with a mandatory deterministic fallback | Accepted | 2026-07-07 |
| [ADR-003](ADR-003-ui-stack-tokens-vanilla.md) | UI stack: token CSS + scoped CSS + vanilla-JS component registry (no framework) | Accepted | 2026-07-07 |
| [ADR-004](ADR-004-single-user-first-scale-seams.md) | Build v1 single-user, keep four named seams clean for the Stage-2 multi-user service | Accepted | 2026-07-07 |
| [ADR-005](ADR-005-exercise-interaction-contract.md) | The exercise/interaction JSON contract (one seam, three consumers) | Proposed | 2026-07-07 |
| [ADR-006](ADR-006-data-model-file-store-schema.md) | Data model & file-store schema (records, IDs, on-disk layout) | Proposed | 2026-07-07 |
| [ADR-007](ADR-007-mastery-and-selection-algorithm.md) | Mastery model & adaptive selection algorithm | Proposed | 2026-07-07 |
| [ADR-008](ADR-008-error-classifier-alignment-taxonomy.md) | Error classifier: alignment + tag taxonomy | Proposed | 2026-07-07 |
| [ADR-009](ADR-009-session-lifecycle-state.md) | Session lifecycle & where in-flight state lives | Proposed | 2026-07-07 |
| [ADR-010](ADR-010-frontend-app-architecture.md) | Frontend app architecture (SPA shell, registry, router, audio wrapper) | Proposed | 2026-07-07 |
| [ADR-011](ADR-011-rewards-gamification-economy.md) | Rewards & gamification economy | Proposed | 2026-07-07 |
| [ADR-012](ADR-012-agent-integration-contract.md) | Agent integration contract (tool-use, PII boundary, caching, fallback) | Proposed | 2026-07-07 |

> Number monotonically; never reuse. One file per ADR: `ADR-NNN-short-slug.md`.

## Stage-1 ADR roadmap — lock order & gates
ADRs 005–012 are the "lowered-altitude" build contracts derived from `PLAN.md` (proposed 2026-07-07; all target **Stage 1 / single-user** only). Lock order follows the build dependency chain:

| Order | ADR | Locks before | Gate to accept |
|-------|-----|--------------|----------------|
| 1 | **006** data model | store (EW2) | owner nod (mechanical) |
| 2 | **005** exercise contract | API/UI/agent (B6/B7/B8) | owner nod (mechanical) |
| 3 | **008** classifier taxonomy | skills (B3/B5) | **owner sign-off** (pedagogy; tag set is permanent) |
| 4 | **007** mastery + selection | selector (B3/B4) | **owner sign-off + 2nd-ideator** (pedagogy-critical numbers) |
| 5 | **009** session lifecycle | session API (B6) | owner nod (architectural) |
| 6 | **011** rewards economy | rewards (B9) | owner sign-off (tuning the fun) |
| 7 | **010** frontend architecture | UI (B7) | owner nod (architectural) |
| 8 | **012** agent integration | agent (B8) | owner nod (builds on ADR-002) |

Mechanical/architectural ADRs the owner can rubber-stamp; the three flagged **pedagogy** ones (007, 008, 011) are where the owner's input actually changes the child's experience — review those first.
