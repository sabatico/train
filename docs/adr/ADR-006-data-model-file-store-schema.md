# ADR-006 — Data model & file-store schema (record shapes, IDs, on-disk layout)

**Status:** Proposed *(lock before EW2/B3 — the store is built against it)*
**Date:** 2026-07-07 · **Related:** ADR-001 (file store), ADR-004 (`student_id` seam), `PLAN.md` §2/§5

## Context
ADR-001 chose file-JSON; ADR-004 requires `student_id` on every record so the Stage-2 DB swap is a backend change, not a caller change. Before `store.py` (EW2) and the skill model (B3) exist, the exact record shapes and the on-disk layout must be frozen — data written in the wrong shape is expensive to migrate once the child has real history (invariant #1: no data loss).

## Decision
**On-disk layout — partitioned by `student_id` from day one** (v1 has one dir, `default/`):
```
data/
├── students/
│   └── default/
│       ├── profile.json      # name, avatar, settings (TTS voice/rate, font, session length)
│       ├── skills.json       # { "skills": { "<skill_id>": <skill record> } }
│       ├── rewards.json      # stars total, level, xp, streak, freeze tokens, collection
│       ├── memory.md         # the agent's teacher notebook (append-only, dated)
│       ├── sessions/
│       │   ├── current.json  # the in-flight session (ADR-009); absent when idle
│       │   └── 2026-07-08.json … # completed session logs (item-by-item, attempts, tags, stars)
│       └── logs/app.log
└── word_bank/                # SHARED content, not per-student (tracked in git)
    ├── short_vowels.json …   # one file per skill/pattern
```
Only `word_bank/` is committed; everything under `students/` is gitignored runtime data.

**Record schemas (the frozen shapes):**
- **skill record** (per `PLAN.md` §2): `{ id, mastery:0-100, last_practiced, exposures, streak, introduced:bool, decay_per_day }` — semantics fixed by ADR-007.
- **word_bank entry:** `{ "word":"hope", "phonemes":["h","o","p"], "pattern":"magic_e", "tricky_letters":[3], "phrase":"i hope so", "sentence":"I hope it is sunny.", "emoji":"🤞", "distractors":["b","d"] }`. `tricky_letters` = index list for heart-word ❤️ markers; `pattern` ties the word to its skill.
- **completed session log:** `{ student_id, date, session_id, focus_skill, items:[{item_id,type,skill_id,target,attempts:[{attempt,phase,tags,correct,replays}],stars}], totals:{stars,items,accuracy}, agent:{plan_source, notes} }`.
- **rewards:** `{ stars_total, xp, level, level_name, streak:{count,last_day,freezes}, collection:[{skill_id, creature_id, hatched_on}] }` (economy = ADR-011).
- **profile:** `{ display_name, avatar, settings:{ tts_voice, tts_rate, font_scale, items_per_session } }`.

**Storage contract (`engine/store.py` — the ONLY module that touches these files):**
- Every read/write takes `student_id` as its first argument. No caller assumes "default".
- Writes are atomic: write `*.tmp` in the same dir → `os.replace()` (POSIX-atomic rename). Never partial-write a live file (invariant #1).
- Reads of a missing file return a typed default (empty skills, fresh rewards), never crash — the app must run on a brand-new student dir.
- `memory.md` and session logs are append-oriented; skills/rewards/profile are read-modify-write-whole.
- A guardrail test (owner-owned) asserts: no other module opens `data/` for writing, and no store call lacks `student_id`.

## Alternatives rejected
- **One big `state.json` per student** — simpler, but every tiny mastery tick rewrites the whole blob (more corruption surface) and the parent can't read a clean per-concern file. Splitting by concern keeps writes small and files human-readable (the ADR-001 rationale).
- **Flat files not partitioned by student** (`skills.json` at data root) — fine for one child, but violates the ADR-004 seam; adding the `students/<id>/` layer later means moving every file and rewriting every path. The empty layer costs nothing now.
- **SQLite now** — re-litigates ADR-001; the `store.py` seam already makes that a contained future swap.

## Consequences
- **Makes easy:** brand-new-student bootstrap (create dir, defaults fill in); Stage-2 multi-student (`students/<id>/`) and DB swap (reimplement `store.py`); trivial backup (copy `data/students/`).
- **Makes hard / costs:** cross-file consistency is the caller's job (mitigated: schemas are designed so no write spans two files atomically).
- **Follow-ups:** ship `store.py` + guardrail suite as EW2 before any engine module; a `bootstrap_student()` that lays down defaults.
- **Risks accepted:** schema evolution (adding a field to skill records) — handle with tolerant readers (unknown/missing fields defaulted), not migrations, while v1 is single-user.
