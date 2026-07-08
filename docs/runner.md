# Runner — Wave 1: Foundation (design → skeleton → first exercises → agent wired)

> **The live accountability tracker for the work in flight.** One runner per "wave" (a milestone, a refactor, a review round, a feedback batch). When a wave closes, archive/supersede it and open the next. **Keep statuses current as part of Done.**
> **Status keys:** ☐ todo · ❓ blocked on a decision/answer · ◐ in design · ▶ in progress · ✅ done.

## A. Easy wins — low-risk, ship first
| ID | Item | Source | Status | Notes |
|----|------|--------|--------|-------|
| EW1 | Repo scaffolding: `.gitignore`, `requirements.txt`, venv, Flask `app.py` (health + tenancy-shaped routes) | IN-1 | ✅ | done act-009; `/healthz`, `/`→`/app`, `/parent` verified |
| EW2 | `data/` layout + storage module with atomic writes (`engine/store.py`) | ✅ | done act-009; lead-authored (invariant #1), Sonnet cross-authored 82 tests, `store.py` 100% cov (incl. atomic-write failure paths + traversal + guardrail); `config.py`/`models.py` 100% |
| EW3 | Seed word banks: `short_vowels`, `digraphs`, `heart_words` (~120 words with phonemes, phrase, sentence, emoji) | ▶ | 3 banks seeded (28 words: short_vowels 8, digraphs 10, heart_words 10) + `skill_graph.json`; expansion toward ~120 + more patterns still owed (backlog T-005) |

## B. Bigger items — design before building (ADR if consequential)
| ID | Item | Source | Status | Direction |
|----|------|--------|--------|-----------|
| B1 | `DESIGN_BRIEF.md` for Claude Design (screens, interactions, principles, styling manifest) | IN-2 | ✅ | done 2026-07-07; owner takes it to Claude Design |
| B2 | Claude Design mockups → token-lock pass (`tokens.css` + primitives) | IN-2 | ☐ | UNBLOCKED — handoff landed in `design_handoff_spell_quest/` (tokens.css + components.css + 2 `.dc.html` references); verify tokens against the rendered references per `sops/mockup-implementation.md` Step 0, then adopt into `static/css/` |
| B3 | Skill model + decay + prerequisite gates (`engine/skills.py`) | PLAN §2 | ✅ | done act-010; ADR-007; 100% cov; lazy-projection decay, one-way intro latch |
| B4 | Adaptive selector 60/30/10 + scaffold ladder (`engine/selector.py`) | PLAN §2 | ✅ | done act-010; ADR-007; 100% cov; deterministic (seeded rng); step-down is runtime (B6) |
| B5 | Error classifier with alignment + tags (`engine/classifier.py`) | PLAN §4 | ✅ | done act-010; ADR-008; 100% cov; frozen 9-tag enum, phoneme-aware |
| B6 | Session builder + Flask API (start session / next item / submit answer) | ✅ | done act-011; ADR-005/009; `engine/contracts.py` (100%) + `engine/session.py` (100%) + `/api/session/*` routes; server-authoritative grading, correction routine, step-down, resume, hatching. Contract tool-schemas verified against live DeepSeek function-calling |
| B7 | UI shell + component registry + first 3 exercises (`word_builder`, `letter_boxes`, `echo_dictation`) + browser TTS | PLAN §3 | ☐ | after B2 token-lock; zero inline styles; NEVER copy the `.dc.html` reference markup (inline-styled design-tool output — rebuild on tokens/components per the SOP) |
| B10 | Parent screens (P1 dashboard, P2 settings) design round — NOT in the current handoff bundle, nor the §8 state set (loading/empty/TTS-fallback) | handoff README | ❓ | owner runs a second Claude Design round for P1/P2 + states when kid screens are underway |
| B8 | DeepSeek agent module: session-plan call, kid-voice feedback call, `memory.md` notebook, engine fallback (`agent/teacher.py`) | ADR-002/012 | ▶ | `agent/client.py` built; **live function-calling with the contract tool-schemas VERIFIED** (returns emit_word_builder/emit_echo_dictation tool_calls). Next: `agent/teacher.py` (plan enrich + kid-voice feedback + memory) wired into session with engine fallback + PII guardrail |
| B9 | Rewards engine: stars, chest, streak, levels (`engine/rewards.py`) | ✅ | done act-010; ADR-011; 100% cov; add-only (rejects negatives), streak-freeze SM, sustained-mastery hatching. UI reward screens still owed (B7) |

## B'. Stage-1 ADRs — ALL ACCEPTED 2026-07-07 (on owner "proceed")
ADR-005..012 accepted; build items may proceed against them. ADR-007 got an inline second-ideator pass that fixed a compounding-decay bug (now a lazy projection) and premature-unlock (gate checks effective mastery at session end; `introduced` is a one-way latch; new skills start at 20). Pedagogy constants remain tunable in `engine/config.py` without a new ADR. Details: `docs/adr/README.md`.

## C. Open questions (blocking the above)
1. ~~Claude Design mockups + structured handoff~~ → RESOLVED 2026-07-07: handoff received (`design_handoff_spell_quest/`), kid screens complete; parent screens + §8 states still owed (B10).
2. ~~`DEEPSEEK_API_KEY`~~ → RESOLVED 2026-07-07: key in `.env`, probe verified (TBD-001 closed). Also unblocks the Sonnet↔DeepSeek cross-author pairing (CLAUDE.md model policy) once the wrapper script exists.
3. Child's browser + TTS accent preference → blocks final dictation tuning only.

## D. Review/correction log (append per review or owner-correction round)
- 2026-07-07 — CR1 (owner): plan is ONE phase, AI from the start, DeepSeek APIs (not Claude API); UI+backend first, connect the key after. PLAN.md updated accordingly.

> Sources: `F#` = findings (from a walkthrough/review); `IN-x` = owner input; `CR#` = correction round. Link items to their ADRs/commits.
