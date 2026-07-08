# Build Tracker — Spell Quest

> The coarse progress ledger: what's built vs planned, wave by wave. Finer grain lives in `runner.md` (in-flight) and `feature-catalog.md` (per capability). Update at the end of every act.
> **Last updated:** 2026-07-07.

## Overall
| Area | Progress | Notes |
|------|----------|-------|
| Harness / docs | ✅ installed | constitution, running files, SOPs, PLAN.md, DESIGN_BRIEF.md |
| Architecture (ADRs) | 🔨 | ADR-001..004 Accepted; ADR-005..012 (Stage-1 build contracts) Proposed, awaiting owner lock — roadmap in adr/README.md |
| UI design (Claude Design mockups) | 🔨 | kid screens + 10 exercises received (`design_handoff_spell_quest/`); parent P1/P2 + §8 states owed (B10) |
| Backend engine (`engine/`) | 🔨 | store + config + models built & tested (100% cov); skills/selector/classifier/session/rewards owed (B3–B6, B9) |
| Flask API (`app.py`) | 🔨 | skeleton (health + tenancy routes + factory + bootstrap); session endpoints owed (B6) |
| Frontend (shell + exercises) | ⬜ | blocked on token-lock from mockups |
| Teacher agent (`agent/`) | ⬜ | mocked until `DEEPSEEK_API_KEY` |
| Word banks | ⬜ | Wave 1 target: ~120 words / 3 banks |
| Tests + gates | 🔨 | 82 tests green, 99% overall; invariant-#1 guardrail (no data writes outside store) in place; CI gate scripts still owed (T-008) |

## Wave log
- **Wave 1 — Foundation** (open, 2026-07-07 → ): design brief ✅ → mockups → token-lock → engine skeleton + API + 3 exercises + agent module. Tracker: `runner.md`.
