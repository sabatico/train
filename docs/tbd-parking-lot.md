# TBD Parking Lot — Deliberately-Deferred Work — Spell Quest

> **Everything we consciously decided to develop *later* because of a constraint** — not forgotten, not unscheduled-by-accident, but **deferred on purpose** with a reason and a resurface trigger. The "we know, and here's why we're not doing it yet" list.
> **Distinct from `backlog-tickets.md`:** the backlog is "intend to do, just queued." This is "**blocked/punted by a specific constraint** — revisit when the constraint changes."
> **Distinct from `deferred-test-registry.md`:** that is specifically *owed test coverage*. This is *owed product/engineering work* of any kind.

Each item names **the constraint** (why now is wrong) and **the resurface trigger** (what flips it back into play) — so it can't rot silently and it comes back automatically when its blocker lifts.

| ID | Item | Why deferred (the constraint) | Resurface trigger | Code marker | Notes |
|----|------|-------------------------------|-------------------|-------------|-------|
| TBD-002 | Final TTS voice/rate tuning for dictation | Don't know the child's actual browser/accent preference yet (ONBOARDING §5 Q1/Q2) | Owner answers → tune `profile.json` defaults | — | voices differ wildly per browser |
| TBD-003 | Multi-child support (profiles, separate data dirs) | v1 is deliberately single-child — one learner, one `data/`; generalizing now adds complexity with zero users for it | A second child starts using the app | — | deliberate scope cut |
| TBD-004 | Auth / network exposure (serve beyond localhost) | App is localhost-only on the family Mac; adding auth now is cost without threat | Owner wants tablet/remote access on the home network | — | if it ships, PAR dashboard gets the gate first |

## Categories that commonly land here
- **Blocked on an external dependency** (a vendor sandbox, an unbuilt module, an approval, a license).
- **Blocked on a decision** (an ADR not yet made — cross-link the open question in ONBOARDING §5).
- **Gated by a milestone** (don't do X before the security/audit/perf gate).
- **Deliberate scope cuts** (a v1 simplification).
- **Cost/risk punts** (worth doing, not worth the spend/risk yet).

## Rules
1. **A code site that's intentionally incomplete gets a `TBD:` marker** pointing here (optionally a CI check, like the deferred-test registry).
2. **When the resurface trigger fires, the item moves to `backlog-tickets.md`** (or straight into the active runner) — and the row is deleted here.
3. Review the triggers at each milestone so nothing stays parked past its constraint.
