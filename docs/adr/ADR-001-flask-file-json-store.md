# ADR-001 — Python/Flask backend with a file-based JSON store

**Status:** Accepted
**Date:** 2026-07-07 · **Related:** `PLAN.md` §5, `docs/architecture.md`, invariant #1 in `CLAUDE.md`

## Context
Single-user (one child, one parent), single-machine app with tiny write volume (one 10–15-minute session/day). The owner explicitly prefers Python/Flask and a file database. The data (skill states, session logs, the agent's teacher notebook) benefits enormously from being human-readable — the parent should be able to open any file and understand it. Agent-buildability matters: the stack must be one cheaper builder models can't get subtly wrong.

## Decision
Flask serves both the API and the static frontend. All state lives as JSON/Markdown files under `data/` (see `docs/architecture.md` §1 for the layout). Every write goes through a single storage module (`engine/store.py`) using atomic tmp-file + `os.rename`, so a crash can never leave a half-written file. No other module opens `data/` files for writing.

## Alternatives rejected
- **SQLite** — more robust querying, but the data is small, the query needs are trivial, and files-you-can-read beats a binary blob for a parent auditing their child's learning history. Fallback: if querying session history ever hurts, sessions/ migrates to SQLite behind `store.py` without touching callers.
- **Django / FastAPI** — Django is oversized for this; FastAPI is fine but Flask is the owner's stated preference and the most-trained target for builder agents.
- **A hosted DB / cloud backend** — violates the spirit of invariant #2 (child data stays home) and adds accounts/cost/latency for zero benefit at n=1 users.

## Consequences
- **Makes easy:** hand-editing word banks and settings; git-diffable state; trivial backups (copy `data/`); zero infra.
- **Makes hard / costs:** no transactions across multiple files (mitigate: keep each write single-file; design state so cross-file consistency isn't required); no concurrent writers (fine: one child, one server process).
- **Follow-ups:** build `store.py` + its owner-owned guardrail tests first (runner EW2).
- **Risks accepted:** filesystem-level corruption (mitigated by atomic writes + easy backups).
