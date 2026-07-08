# Feature & Module Catalog — Spell Quest

> **The ONE enumerable inventory of everything the product does** — user-facing features (Part A) and core/internal modules (Part B) — with status, where it lives, and how it's tested. Built so anyone can answer *"what does this do, end to end?"* without stitching five docs together. Gives every capability a **stable ID** to plan/audit/experiment against.
> **⚠️ Maintenance is part of Done:** when a slice adds/changes/removes a capability, update its row **in the same slice**. A stale catalog is a bug.

**Status legend:** ✅ done & wired · 🔨 partial (e.g. backend only) · ⛔ gated/blocked on an external dep · ⬜ planned.

## Part A — User-facing features (by persona/area)

### The child (the learner)
| ID | Feature | Status | Surface (screen / route / CLI) | Key endpoints / entrypoints | Tests | Notes |
|----|---------|--------|--------------------------------|-----------------------------|-------|-------|
| KID-01 | Start a daily session (welcome, streak, mission) | ⬜ | Home screen `/` | `POST /api/session/start` | — | PLAN §7 step 1 |
| KID-02 | Warm-up items (guaranteed early wins) | ⬜ | Session screen | session builder | — | PLAN §7 step 2 |
| KID-03 | Teach card (focus-pattern mini-lesson) | ⬜ | Session screen | agent-written or canned | — | PLAN §7 step 3 |
| KID-04 | `word_builder` exercise (tap letter tiles into sound boxes) | ⬜ | Session screen | component registry | — | PLAN §3 #1 |
| KID-05 | `letter_boxes` exercise (one input per letter, phoneme-grouped) | ⬜ | Session screen | component registry | — | PLAN §3 #2 |
| KID-06 | `missing_letters` exercise (pattern cloze) | ⬜ | Session screen | component registry | — | PLAN §3 #3 |
| KID-07 | `bd_ninja` game (b/d discrimination, the only timed exercise) | ⬜ | Session screen | component registry | — | PLAN §3 #4 |
| KID-08 | `word_sort` exercise (drag into pattern buckets) | ⬜ | Session screen | component registry | — | PLAN §3 #5 |
| KID-09 | `heart_word_spotlight` (look-cover-write-check with ❤️ letters) | ⬜ | Session screen | component registry | — | PLAN §3 #6 |
| KID-10 | `echo_dictation` (TTS word → free input, unlimited 🔊 replay) | ⬜ | Session screen | browser `speechSynthesis` | — | PLAN §3 #7 |
| KID-11 | `phrase_dictation` (TTS phrase → per-word inputs) | ⬜ | Session screen | component registry | — | PLAN §3 #8 |
| KID-12 | `sentence_scribe` (free writing + gentle AI review, max 2 corrections) | ⬜ | Session screen | agent review call | — | PLAN §3 #9 |
| KID-13 | `beat_yesterday` sprint (mastered words, beat own record) | ⬜ | Session screen | component registry | — | PLAN §3 #10 |
| KID-14 | Correction routine (attempt vanishes → correct form + why → retype right) | ⬜ | Overlay in every exercise | classifier + feedback | — | invariant #3; PLAN §3 |
| KID-15 | Reward screen (chest, stars, level progress) + level-up celebration | ⬜ | End-of-session screen | `engine/rewards.py` | — | PLAN §6 |
| KID-16 | Creature/sticker collection shelf (one per mastered pattern) | ⬜ | Collection screen | rewards + skills | — | PLAN §6 |
| KID-17 | Streak flame with freeze token | ⬜ | Home screen | rewards | — | PLAN §6 |

### The parent (the owner)
| ID | Feature | Status | Surface | Key endpoints / entrypoints | Tests | Notes |
|----|---------|--------|---------|-----------------------------|-------|-------|
| PAR-01 | Rose-of-winds radar chart of the 14 skills | ⬜ | Parent dashboard `/parent` | `GET /api/skills` | — | PLAN §2 |
| PAR-02 | Session history + error log browser | ⬜ | Parent dashboard | `data/sessions/*` | — | |
| PAR-03 | Agent's teacher notebook + weekly note | ⬜ | Parent dashboard | `data/memory.md` | — | key live; unblocked |
| PAR-04 | Settings (TTS voice/rate, font size, session length) | ⬜ | Parent dashboard | `data/profile.json` | — | |

## Part B — Core / internal modules
| ID | Module | Status | Path | Responsibility | Tests | Notes |
|----|--------|--------|------|----------------|-------|-------|
| CORE-01 | Storage (atomic file-JSON reads/writes) | ⬜ | `engine/store.py` | ALL `data/` I/O; invariant #1 | — | guardrail tests owner-owned |
| CORE-02 | Skill model (mastery EMA, decay, prerequisite gates) | ⬜ | `engine/skills.py` | the rose of winds | — | PLAN §2 |
| CORE-03 | Adaptive selector (60/30/10 + step-down ladder) | ⬜ | `engine/selector.py` | what to practice next | — | PLAN §2 |
| CORE-04 | Error classifier (alignment + error tags) | ⬜ | `engine/classifier.py` | attempt→tags→skill signals | — | PLAN §4 |
| CORE-05 | Session builder (warmup→teach→practice→challenge→reward) | ⬜ | `engine/session.py` | assembling a session | — | PLAN §7 |
| CORE-06 | Rewards (stars, chest, streak, levels, collection) | ⬜ | `engine/rewards.py` | invariant #3 half-owner | — | PLAN §6 |
| CORE-07 | Teacher agent (DeepSeek: plan, feedback, notebook; engine fallback) | ⬜ | `agent/teacher.py` | the AI layer | — | key live (2026-07-07); build against real API |
| CORE-08 | Flask API + routes | ⬜ | `app.py` | HTTP seam UI⇄engine | — | contract frozen before B7 |
| CORE-09 | UI shell + component registry + tokens | ⬜ | `static/`, `templates/` | render `{type,payload}` | — | ADR-003; zero inline styles |
| CORE-10 | Word banks (curated pattern lists) | ⬜ | `data/word_bank/*.json` | content, not code | — | reviewed by owner |

## Stub / intentionally-incomplete inventory
| Marker | What's stubbed | Why (the external gate) | Where it's tracked |
|--------|----------------|-------------------------|--------------------|
| `STUB:DEEPSEEK` | Live DeepSeek API calls (mocked client until then) | owner has not yet provided `DEEPSEEK_API_KEY` | `docs/third-party-services.md`, runner C2 |
