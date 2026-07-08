# Runner — Wave 1: Foundation (design → skeleton → first exercises → agent wired)

> **The live accountability tracker for the work in flight.** One runner per "wave" (a milestone, a refactor, a review round, a feedback batch). When a wave closes, archive/supersede it and open the next. **Keep statuses current as part of Done.**
> **Status keys:** ☐ todo · ❓ blocked on a decision/answer · ◐ in design · ▶ in progress · ✅ done.

## A. Easy wins — low-risk, ship first
| ID | Item | Source | Status | Notes |
|----|------|--------|--------|-------|
| EW1 | Repo scaffolding: `.gitignore`, `requirements.txt`, venv, empty Flask `app.py` that serves a hello page | IN-1 | ☐ | trivial, unblocks everything |
| EW2 | `data/` layout + storage module with atomic writes (`engine/store.py`) | IN-1 | ☐ | invariant #1 lives here; guardrail test with it |
| EW3 | Seed word banks: `short_vowels`, `digraphs`, `heart_words` (~120 words with phonemes, phrase, sentence, emoji) | PLAN §5 | ☐ | curated content, no code risk |

## B. Bigger items — design before building (ADR if consequential)
| ID | Item | Source | Status | Direction |
|----|------|--------|--------|-----------|
| B1 | `DESIGN_BRIEF.md` for Claude Design (screens, interactions, principles, styling manifest) | IN-2 | ✅ | done 2026-07-07; owner takes it to Claude Design |
| B2 | Claude Design mockups → token-lock pass (`tokens.css` + primitives) | IN-2 | ❓ | blocked on C1 (mockups); follow `sops/mockup-implementation.md` |
| B3 | Skill model + decay + prerequisite gates (`engine/skills.py`, `data/skills.json`) | PLAN §2 | ☐ | per ADR-001; pure functions, heavy unit tests |
| B4 | Adaptive selector 60/30/10 + step-down ladder (`engine/selector.py`) | PLAN §2 | ☐ | deterministic; agent may override later |
| B5 | Error classifier with alignment + tags (`engine/classifier.py`) | PLAN §4 | ☐ | pure function; richest test target |
| B6 | Session builder + Flask API (start session / next item / submit answer) | PLAN §7 | ☐ | freeze the exercise JSON contract first (it's the seam with the UI **and** the agent tools) |
| B7 | UI shell + component registry + first 3 exercises (`word_builder`, `letter_boxes`, `echo_dictation`) + browser TTS | PLAN §3 | ❓ | after B2 token-lock; zero inline styles |
| B8 | DeepSeek agent module: session-plan call, kid-voice feedback call, `memory.md` notebook, engine fallback (`agent/teacher.py`) | ADR-002 | ☐ | build against a mocked client; `STUB:DEEPSEEK` until key arrives |
| B9 | Rewards engine: stars, chest, streak, levels (`engine/rewards.py`) | PLAN §6 | ☐ | invariant #3: never subtract earned rewards |

## C. Open questions (blocking the above)
1. Claude Design mockups + structured handoff (owner runs the brief through Claude Design) → blocks B2/B7.
2. `DEEPSEEK_API_KEY` (owner will provide) → blocks live agent calls; B8 proceeds mocked.
3. Child's browser + TTS accent preference → blocks final dictation tuning only.

## D. Review/correction log (append per review or owner-correction round)
- 2026-07-07 — CR1 (owner): plan is ONE phase, AI from the start, DeepSeek APIs (not Claude API); UI+backend first, connect the key after. PLAN.md updated accordingly.

> Sources: `F#` = findings (from a walkthrough/review); `IN-x` = owner input; `CR#` = correction round. Link items to their ADRs/commits.
