# ADR-004 — Build v1 single-user, but keep four named seams clean for the Stage-2 multi-user service

**Status:** Accepted
**Date:** 2026-07-07 · **Related:** ADR-001 (file store), ADR-003 (UI stack), `docs/tbd-parking-lot.md` TBD-005/006/007, `PLAN.md` §10

## Context
The owner declared the staged direction (2026-07-07): Stage 2 wraps the app in Mac/Android WebView shells for push notifications and turns it into a **multi-user service — parent and kid accounts, billing, scalable to ~10k users**. Stage 2 is explicitly later; v1 remains the single-child local app. The risk to manage NOW is architectural lock-in: single-user assumptions (a global "the student", direct file paths, server-rendered state) that would turn the Stage-2 migration into a rewrite. The opposite risk is real too: prematurely building tenancy/auth/DB for one child is cost and complexity with zero current users.

## Decision
v1 stays single-user, file-based, local (ADR-001 unchanged). But four seams are **build rules from the first line of code**:
1. **Every `engine/store.py` call and every data record carries a `student_id`** (constant `"default"` in v1). No module ever assumes "the one student". At 10k users, `store.py`'s file backend is swapped for Postgres behind the same interface — callers untouched.
2. **The Flask API is the only UI⇄backend channel and is stateless per request** (no server globals, no in-process session state; all state persists via `store.py`). A stateless API layer scales horizontally without redesign.
3. **Route namespaces are tenancy-shaped now:** kid surfaces under `/app/*` + `/api/*`, parent surfaces under `/parent/*` — so auth middleware and role checks (parent vs kid) bolt onto existing boundaries instead of a route refactor.
4. **The frontend is a pure API client** (already true via ADR-003's `{type,payload}` registry) and must stay **WebView-clean**: no browser-chrome dependencies, no popups/new-tabs, TTS behind one wrapper module (`speech.js`) so a native TTS/push bridge can replace it inside the WebView shells.

Explicitly NOT built in v1: accounts/auth, billing, a real DB, push notifications, phone layouts, multi-tenancy plumbing beyond the `student_id` parameter. That work is parked (TBD-005/006/007) and resurfaces when the owner declares Stage 2.

## Alternatives rejected
- **Build multi-user now** — months of auth/billing/DB work before the child gets her first session; the only current user needs a spelling trainer, not a SaaS.
- **Ignore scale entirely, refactor later** — the four seams above cost ~zero now (a parameter, a discipline, a naming scheme, a wrapper module) but are brutally expensive to retrofit once violated everywhere. Cheap insurance beats a rewrite.
- **Jump straight to Postgres now (skip file DB)** — re-litigates ADR-001; the file store is the right v1 call (human-readable, zero infra) and the `store.py` seam makes the swap contained.

## Consequences
- **Makes easy:** the Stage-2 migration becomes: swap store backend + add auth middleware on existing namespaces + add billing service + wrap in WebView shells — additive, not surgical.
- **Makes hard / costs:** slight ceremony in v1 (`student_id` everywhere; TTS behind a wrapper).
- **Follow-ups:** guardrail lint/test: no direct `data/` file access outside `store.py`, and every store API requires `student_id`. `DESIGN_BRIEF` B10 round should note Android-WebView (phone-width) as a future viewport.
- **Risks accepted:** 10k-user needs we can't foresee (queues, caching, rate limits) will still need Stage-2 design work — these seams make that work possible, not free.
