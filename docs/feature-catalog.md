# Feature & Module Catalog — Spell Quest

> **The ONE enumerable inventory of everything the product does** — user-facing features (Part A) and core/internal modules (Part B) — with status, where it lives, and how it's tested. Built so anyone can answer *"what does this do, end to end?"* without stitching five docs together. Gives every capability a **stable ID** to plan/audit/experiment against.
> **⚠️ Maintenance is part of Done:** when a slice adds/changes/removes a capability, update its row **in the same slice**. A stale catalog is a bug.

**Status legend:** ✅ done & wired · 🔨 partial (e.g. backend only) · ⛔ gated/blocked on an external dep · ⬜ planned.
**Tests column:** ✅ automated + measured · 🖥️ browser/manual-verified only (automated JS tests deferred, T-010) · — none yet.

## Part A — User-facing features (by persona/area)

### The child (the learner)
| ID | Feature | Status | Surface (screen / route / CLI) | Key endpoints / entrypoints | Tests | Notes |
|----|---------|--------|--------------------------------|-----------------------------|-------|-------|
| KID-01 | Start a daily session (welcome + Start button) | ✅ | Home screen `/app` | `POST /api/session/start` | 🖥️ | streak/mission chips still to add; browser-verified |
| KID-02 | Warm-up items (guaranteed early wins) | ⬜ | Session screen | session builder | — | PLAN §7 step 2 |
| KID-03 | Teach card (focus-pattern mini-lesson) | ✅ | Session screen | canned (agent enrich later) | 🖥️ | browser-verified; PLAN §7 step 3 |
| KID-04 | `word_builder` exercise (tap letter tiles into sound boxes) | ✅ | Session screen | `exercises.js` registry | 🖥️ | browser-verified tile→box interaction |
| KID-05 | `letter_boxes` exercise (one input per letter, phoneme-grouped) | ✅ | Session screen | `exercises.js` registry | 🖥️ | renderer verified; auto-advance typing |
| KID-06 | `missing_letters` exercise (pattern cloze) | ⬜ | Session screen | component registry | — | PLAN §3 #3 |
| KID-07 | `bd_ninja` game (b/d discrimination, the only timed exercise) | ⬜ | Session screen | component registry | — | PLAN §3 #4 |
| KID-08 | `word_sort` exercise (drag into pattern buckets) | ⬜ | Session screen | component registry | — | PLAN §3 #5 |
| KID-09 | `heart_word_spotlight` (look-cover-write-check with ❤️ letters) | ⬜ | Session screen | component registry | — | PLAN §3 #6 |
| KID-10 | `echo_dictation` (TTS word → free input, unlimited 🔊 replay) | ✅ | Session screen | `speech.js` + registry | 🖥️ | renderer verified; auto-speak + replay |
| KID-11 | `phrase_dictation` (TTS phrase → per-word inputs) | ⬜ | Session screen | component registry | — | PLAN §3 #8 |
| KID-12 | `sentence_scribe` (free writing + gentle AI review, max 2 corrections) | ⬜ | Session screen | agent review call | — | PLAN §3 #9 |
| KID-13 | `beat_yesterday` sprint (mastered words, beat own record) | ⬜ | Session screen | component registry | — | PLAN §3 #10 |
| KID-14 | Correction routine (attempt vanishes → correct form + why → retype right) | ✅ | `correction.js` overlay | classifier + agent/canned why | 🖥️ | browser-verified: shows correct word w/ hot letters, retype advances; invariant #3 |
| KID-15 | Reward screen (stars, level progress, hatch tease) | ✅ | End-of-session screen | `engine/rewards.py` | 🖥️ | browser-verified ⭐ count + level; confetti/chest polish later |
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
| CORE-01 | Storage (atomic file-JSON reads/writes) | ✅ | `engine/store.py` | ALL `data/` I/O; invariant #1 | ✅ | 82 cross-authored tests, 100% cov; atomic write, traversal-safe, idempotent bootstrap, guardrail (no data writes outside store). `config.py`+`models.py` (100%) alongside |
| CORE-02 | Skill model (mastery EMA, decay, prerequisite gates) | ✅ | `engine/skills.py` | the rose of winds | ✅ | ADR-007; 100% cov |
| CORE-03 | Adaptive selector (60/30/10 + scaffold ladder) | ✅ | `engine/selector.py` | what to practice next | ✅ | ADR-007; 100% cov; deterministic |
| CORE-04 | Error classifier (alignment + error tags) | ✅ | `engine/classifier.py` | attempt→tags→skill signals | ✅ | ADR-008; 100% cov; frozen tag enum |
| CORE-05 | Session builder (start→teach→practice+correction→finish) | ✅ | `engine/session.py` | assembling + running a session | ✅ | ADR-009; 100% cov; server-authoritative grading, step-down, resume, hatching |
| CORE-11 | Exercise contract (envelope + payloads + validation + tool-schemas) | ✅ | `engine/contracts.py` | the UI⇄API⇄agent seam | ✅ | ADR-005; 100% cov; `public_item` hides answer keys |
| CORE-12 | DeepSeek client (OpenAI-compatible HTTP wrapper) | 🔨 | `agent/client.py` | the provider seam | — | ADR-012; live function-calling verified; tests owed with B8 |
| CORE-06 | Rewards (stars, chest, streak, levels, collection) | ✅ | `engine/rewards.py` | invariant #3 half-owner | ✅ | ADR-011; 100% cov; add-only |
| CORE-07 | Teacher agent (DeepSeek: kid-voice feedback, notebook; engine fallback) | ✅ | `agent/teacher.py` | the AI layer | ✅ | ADR-012; 100% cov; PII-safe, gated, live-verified; plan-enrich later |
| CORE-13 | UI: SPA shell + registry + 3 exercise renderers + correction + TTS | ✅ | `static/js/*` | render `{type,payload}` | 🖥️ | ADR-010; browser-verified; JS unit tests deferred (T-010) |
| CORE-08 | Flask API + routes | ✅ | `app.py` | HTTP seam UI⇄engine | ✅ | `/healthz`, `/`→`/app`, `/parent`, `/api/session/{start,item,answer,finish}`, `/api/skills`; 98% cov (`__main__` guard) |
| CORE-09 | UI tokens + component CSS (design system) | ✅ | `static/css/*`, `templates/` | branding + primitives | 🖥️ | ADR-003/010; adopted from handoff; zero inline styles; `app.css` for gaps |
| CORE-10 | Word banks (curated pattern lists) | 🔨 | `data/word_bank/*.json` | content, not code | n/a | `skill_graph.json` (14-skill prereqs) + `short_vowels.json` (8-word seed); more banks + expansion owed (EW3) |

## Stub / intentionally-incomplete inventory
| Marker | What's stubbed | Why (the external gate) | Where it's tracked |
|--------|----------------|-------------------------|--------------------|
| `STUB:DEEPSEEK` | Live DeepSeek API calls (mocked client until then) | owner has not yet provided `DEEPSEEK_API_KEY` | `docs/third-party-services.md`, runner C2 |
