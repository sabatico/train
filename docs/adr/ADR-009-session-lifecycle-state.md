# ADR-009 — Session lifecycle & where in-flight session state lives

**Status:** Proposed *(lock before B6 — the session API)*
**Date:** 2026-07-07 · **Related:** ADR-004 (stateless API), ADR-005 (item contract), ADR-006 (`current.json`), ADR-007 (selection), `PLAN.md` §7

## Context
ADR-004 forbids server-held per-request state (in-process session objects) so the API scales horizontally at Stage 2. But a session *is* stateful — 8–12 items, a focus pattern, progress, retries, accumulated stars, and it must survive a page refresh or a mid-session "stop for today" (a 7-year-old with ADHD will wander off). Where does that in-flight state live, and what is the lifecycle? This decides the API shape.

## Decision

**In-flight session state is persisted server-side, per student, as `sessions/current.json`** (ADR-006) — not held in process memory, not held only in the client. Each API call is stateless: load `current.json` → mutate → atomic-write → respond. This satisfies ADR-004 (any worker can serve any request) while surviving refreshes and interruptions.

**Lifecycle (state machine):**
```
idle ──start──▶ welcome ──▶ warmup(2) ──▶ teach(1) ──▶ practice(6-8)
                                                          │  ▲ (retry loop, step-down)
                                                          ▼
                                               challenge(0-1, skippable)
                                                          │
                                                          ▼
                                                       reward ──finish──▶ idle
```
- **`POST /api/session/start`** → the selector (ADR-007) builds the item list; the agent may refine ordering/teach copy (ADR-012) within a tight timeout, else engine plan; `current.json` written with the full plan + `cursor=0`. Returns the first item (ADR-005 envelope).
- **`GET /api/session/item`** → returns the item at `cursor` (idempotent; safe on refresh).
- **`POST /api/session/answer`** → server grades against `target`, classifies (ADR-008), updates the item's attempts, computes stars; on miss returns the `reveal` and holds `cursor` for the retype; on success advances `cursor`. Mastery is updated in `skills.json` at answer time (so decay/progress are live).
- **`POST /api/session/finish`** (or auto at end) → writes the completed log `sessions/<date>.json`, updates `rewards.json` (ADR-011), appends an agent note to `memory.md` (ADR-012), deletes `current.json`.
- **Resume:** on `start` while a `current.json` exists (from today, not stale) → offer resume from `cursor` instead of a new plan. Stale (previous day) → archive as abandoned + start fresh.
- **"Stop for today":** just stops calling the API; `current.json` remains for resume. Nothing is lost, nothing is punished (invariant #3).

**The client holds only ephemeral view state** (the current item + animation state); the server is the single source of truth for progress and correctness.

## Alternatives rejected
- **In-process session objects (Flask session / a dict)** — the obvious approach, but it's exactly the server-statefulness ADR-004 rules out, and it loses everything on a server restart or refresh. Rejected on the scale seam.
- **Client-held session state (localStorage, whole plan in the browser)** — survives refresh and is offline-friendly, but ships the answer keys to the client (breaks ADR-005 server-authoritative grading) and makes the parent's cross-device view impossible at Stage 2. Rejected.
- **Signed stateless tokens carrying progress** — clever, keeps the server stateless without a file, but can't hold a growing attempt log and duplicates data the store already persists. Not worth the complexity at n=1.

## Consequences
- **Makes easy:** refresh/interrupt resilience (critical for the ADHD user); horizontal scale later (state is in the store, not the worker); a clean, testable request/response API.
- **Makes hard / costs:** a few extra file reads/writes per item — trivial at one user; at Stage 2 the same reads hit the DB backend (still cheap, indexed by `student_id`).
- **Follow-ups:** define the `current.json` schema with ADR-006; a "stale session" cutoff (same calendar day) constant in `config.py`.
- **Risks accepted:** two browser tabs open on the same student could race `current.json` — acceptable at n=1 (one child, one screen); Stage-2 auth + a session lock handles it then.
