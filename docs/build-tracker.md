# Build Tracker — Spell Quest

> The coarse progress ledger: what's built vs planned, wave by wave. Finer grain lives in `runner.md` (in-flight) and `feature-catalog.md` (per capability). Update at the end of every act.
> **Last updated:** 2026-07-07.

## Overall
| Area | Progress | Notes |
|------|----------|-------|
| Harness / docs | ✅ installed | constitution, running files, SOPs, PLAN.md, DESIGN_BRIEF.md |
| Architecture (ADRs) | 🔨 | ADR-001..004 Accepted; ADR-005..012 (Stage-1 build contracts) Proposed, awaiting owner lock — roadmap in adr/README.md |
| UI design (Claude Design mockups) | 🔨 | kid screens implemented from handoff; parent dashboard hand-built (radar/log/settings) — a designed parent mockup + §8 states still nice-to-have (B10) |
| Backend engine (`engine/`) | ✅ | store/config/models + skills/selector/classifier/rewards + contracts/session all built & tested (100% cov each) |
| Flask API (`app.py`) | ✅ | health + tenancy routes + `/api/session/*` + `/api/skills`; 98% cov |
| Frontend (shell + exercises) | ✅ | SPA shell + registry + 3 renderers + correction + reward + `speech.js`; browser-verified; JS tests deferred (T-010) |
| Teacher agent (`agent/`) | ✅ | `client.py` + `teacher.py` (100% cov); kid-voice feedback wired + live-verified; plan-enrich later (T-012) |
| Word banks | ✅ | 736 words / 9 patterns, sourced online + `scripts/` pipeline + difficulty scores; AI enrichment of phrases/emoji next (T-015) |
| Tests + gates | 🔨 | 264 tests green, 99% overall (100% on every engine module); invariant-#1 guardrail in place; CI gate scripts still owed (T-008) |

## Wave log
- **Wave 1 — Foundation** (2026-07-07): design brief → handoff → token-lock → full deterministic engine (store/config/models/skills/classifier/selector/rewards/contracts/session, 100% cov) + session API + 3 exercises UI + DeepSeek teacher (kid-voice feedback). **Phase-1 core playable end-to-end** (home→teach→exercise→correction→reward), browser-verified. 312 automated tests. Remaining Phase-1 polish + parent dashboard tracked in backlog. Tracker: `runner.md`.
