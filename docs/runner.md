# Runner — Wave 1: Foundation (design → skeleton → first exercises → agent wired)

> **The live accountability tracker for the work in flight.** One runner per "wave" (a milestone, a refactor, a review round, a feedback batch). When a wave closes, archive/supersede it and open the next. **Keep statuses current as part of Done.**
> **Status keys:** ☐ todo · ❓ blocked on a decision/answer · ◐ in design · ▶ in progress · ✅ done.

## A. Easy wins — low-risk, ship first
| ID | Item | Source | Status | Notes |
|----|------|--------|--------|-------|
| EW1 | Repo scaffolding: `.gitignore`, `requirements.txt`, venv, Flask `app.py` (health + tenancy-shaped routes) | IN-1 | ✅ | done act-009; `/healthz`, `/`→`/app`, `/parent` verified |
| EW2 | `data/` layout + storage module with atomic writes (`engine/store.py`) | ✅ | done act-009; lead-authored (invariant #1), Sonnet cross-authored 82 tests, `store.py` 100% cov (incl. atomic-write failure paths + traversal + guardrail); `config.py`/`models.py` 100% |
| EW3 | Word banks with phonemes + difficulty + AI enrichment | ✅ | done act-014/015; **736 words / 9 patterns** sourced online, difficulty-scored (`engine/phonics.py`), selector serves easy→hard. AI-enriched phrase/sentence/emoji for 707/708 words (`agent/enrich.py`). OpenAI-TTS audio still pending (T-014) |

## B. Bigger items — design before building (ADR if consequential)
| ID | Item | Source | Status | Direction |
|----|------|--------|--------|-----------|
| B1 | `DESIGN_BRIEF.md` for Claude Design (screens, interactions, principles, styling manifest) | IN-2 | ✅ | done 2026-07-07; owner takes it to Claude Design |
| B2 | Claude Design mockups → token-lock pass (`tokens.css` + primitives) | IN-2 | ✅ | done act-012; adopted handoff `tokens.css` + `components.css` into `static/css/` verbatim (the designer's implementation source); `app.css` layers app-only widgets, tokens-only |
| B3 | Skill model + decay + prerequisite gates (`engine/skills.py`) | PLAN §2 | ✅ | done act-010; ADR-007; 100% cov; lazy-projection decay, one-way intro latch |
| B4 | Adaptive selector 60/30/10 + scaffold ladder (`engine/selector.py`) | PLAN §2 | ✅ | done act-010; ADR-007; 100% cov; deterministic (seeded rng); step-down is runtime (B6) |
| B5 | Error classifier with alignment + tags (`engine/classifier.py`) | PLAN §4 | ✅ | done act-010; ADR-008; 100% cov; frozen 9-tag enum, phoneme-aware |
| B6 | Session builder + Flask API (start session / next item / submit answer) | ✅ | done act-011; ADR-005/009; `engine/contracts.py` (100%) + `engine/session.py` (100%) + `/api/session/*` routes; server-authoritative grading, correction routine, step-down, resume, hatching. Contract tool-schemas verified against live DeepSeek function-calling |
| B7 | UI shell + component registry + first 3 exercises (`word_builder`, `letter_boxes`, `echo_dictation`) + browser TTS | PLAN §3 | ✅ | done act-012; SPA shell + registry + 3 renderers + correction overlay + reward, `speech.js` TTS wrapper (ADR-004 seam), zero inline styles. **Browser-verified**: full session home→teach→exercises→correction→reward reaches ⭐. JS unit tests deferred (T-010, needs a JS harness) |
| B10 | Parent screens (P1 dashboard, P2 settings) design round — NOT in the current handoff bundle, nor the §8 state set (loading/empty/TTS-fallback) | handoff README | ❓ | owner runs a second Claude Design round for P1/P2 + states when kid screens are underway |
| B8 | DeepSeek agent module: kid-voice feedback, `memory.md` notebook, engine fallback (`agent/teacher.py`) | ADR-002/012 | ✅ | done act-012; `client.py` + `teacher.py` (100% cov), PII-safe prompts, `SPELLQUEST_AGENT_LIVE` gate, wired into the correction routine + notebook. Live kid-voice feedback verified end-to-end. Plan-enrichment/teach-copy left as later enrichment (T-004/T-012) |
| B9 | Rewards engine: stars, chest, streak, levels (`engine/rewards.py`) | ✅ | done act-010; ADR-011; 100% cov; add-only (rejects negatives), streak-freeze SM, sustained-mastery hatching. UI reward screens still owed (B7) |

## B'. Stage-1 ADRs — ALL ACCEPTED 2026-07-07 (on owner "proceed")
ADR-005..012 accepted; build items may proceed against them. ADR-007 got an inline second-ideator pass that fixed a compounding-decay bug (now a lazy projection) and premature-unlock (gate checks effective mastery at session end; `introduced` is a one-way latch; new skills start at 20). Pedagogy constants remain tunable in `engine/config.py` without a new ADR. Details: `docs/adr/README.md`.

## C. Open questions (blocking the above)
1. ~~Claude Design mockups + structured handoff~~ → RESOLVED 2026-07-07: handoff received (`design_handoff_spell_quest/`), kid screens complete; parent screens + §8 states still owed (B10).
2. ~~`DEEPSEEK_API_KEY`~~ → RESOLVED 2026-07-07: key in `.env`, probe verified (TBD-001 closed). Also unblocks the Sonnet↔DeepSeek cross-author pairing (CLAUDE.md model policy) once the wrapper script exists.
3. Child's browser + TTS accent preference → blocks final dictation tuning only.

## E. Post-core Phase-1 additions
| ID | Item | Status | Notes |
|----|------|--------|-------|
| PD1 | Parent dashboard: rose-of-winds SVG radar + weakest-three + error log + settings (`/parent`, `engine/report.py`) | ✅ | done act-013; browser-verified; T-003 satisfied for v1. Cross-authored report tests in progress |

## F. Wave 2 — ADR-014 experience redesign (owner mandate 2026-07-09)
| ID | Item | Status | Notes |
|----|------|--------|-------|
| W2-1 | Needed-vs-exists audit + ADR-014 | ✅ | simulation exposed monotone sessions + 6 unreachable/mistaught capabilities |
| W2-2 | Type rotation + content provider (all 14 skills practicable) | ✅ | selector/config; games capped, phrases/sentences from enriched corpus |
| W2-3 | 6 new exercise types end-to-end (contracts+renderers) | ✅ | missing_letters, word_sort, heart_word_spotlight, phrase_dictation, sentence_scribe, bd_ninja |
| W2-4 | Challenge slot + skip; writing review with whys; memory tail in prompts | ✅ | PLAN §7 shape restored; teacher.review_writing |
| W2-5 | Stars banked at finish (bug: never persisted) + /api/home + gamified home/reward/collection | ✅ | 8-day arc: L4, 7 hatches, streak 8 |
| W2-6 | Cross-authored redesign tests | ✅ | 66 tests, 669 total green; contracts 100%, session 99%, selector 98%; no bugs found |
| W2-7 | beat_yesterday opt-in game | ☐ | T-013; the last PLAN §3 type |
| W2-8 | Answer-flow hardening (anti-trick + typo-cascade responses) | ✅ | act-025; server-derived phase, blank/identical/retype policies, sanitization, bd plausibility, streak guard; **27 cross-authored tests, no bugs** |
| W2-9 | Misleading-image audit (emoji back-translation) + stale-content class kill (served fresh) | ✅ | act-026/027; 557 emojis removed, serving rebuilt from current bank; 59 cross-authored tests |
| W2-10 | Word-picture SVG art: DeepSeek-generated, lead-verified, per depictable word (ADR-015) | ▶ | ~252 drawable; generate→render→visual-verify→apply image fields; wiring done, art generating |

## D. Review/correction log (append per review or owner-correction round)
- 2026-07-09 — CR2 (owner): \"present functionality path has no sense — re-review ALL functionality, redo in full.\" → ADR-014 + Wave 2 (section F). Root complaint validated by simulation; redesign shipped same day.
- 2026-07-07 — CR1 (owner): plan is ONE phase, AI from the start, DeepSeek APIs (not Claude API); UI+backend first, connect the key after. PLAN.md updated accordingly.

> Sources: `F#` = findings (from a walkthrough/review); `IN-x` = owner input; `CR#` = correction round. Link items to their ADRs/commits.
