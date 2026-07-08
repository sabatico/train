# ADR-005 — The exercise/interaction JSON contract (the one seam, three consumers)

**Status:** Accepted *(2026-07-07; the shared-contract seam — frozen before B6/B7/B8)*
**Date:** 2026-07-07 · **Related:** ADR-002 (agent tool schemas), ADR-003 (frontend registry), ADR-004 (stateless API), `PLAN.md` §3, `DESIGN_BRIEF.md` §6

## Context
Three subsystems must agree on exactly one data shape or they drift: (1) the Flask API emits exercise items, (2) the frontend component registry renders them, (3) the DeepSeek agent produces them via tool-use. `architecture.md` already names this the primary contract boundary. If each grows its own shape, the "one schema" promise collapses and every exercise type becomes a three-way integration bug. This is the single highest-leverage thing to freeze before parallel building.

## Decision
One versioned envelope, one payload schema per exercise `type`. **Every item the API sends and every item the agent emits validates against the same JSON Schema** (`engine/contracts/exercise.schema.json`); invalid → rejected (agent output falls back to the deterministic item, ADR-002 rule 2).

**Envelope (every item):**
```json
{
  "contract_version": 1,
  "item_id": "uuid",
  "type": "letter_boxes",
  "skill_id": "magic_e",
  "target": "hope",
  "prompt": { "text": "spell the word", "audio_word": "hope",
              "image_emoji": "🤞", "auto_speak": true },
  "payload": { /* type-specific, schema below */ },
  "grading": { "case_insensitive": true, "trim": true },
  "scaffold_level": 2,
  "why": { "rule_id": "magic_e_v_bodyguard", "text_fallback": "…", "markers": [] },
  "source": "engine" | "agent"
}
```
- `target` is the correct answer (server-authoritative; grading happens server-side — the client never decides correctness, keeping the API the source of truth per ADR-004).
- `why` carries the canned fallback explanation + rule id; the agent may replace `why.text` at feedback time. `markers` = index ranges to highlight (pattern letters / ❤️ heart-word letters), so the correction reveal (DESIGN_BRIEF §5) is data-driven, not hardcoded per word.
- `payload` shape is fixed per `type`. Each of the 10 types (`PLAN.md` §3) gets a named sub-schema, e.g.:
  - `letter_boxes`: `{ "boxes": [{"count":1}], "phoneme_groups": [[0],[1],[2]] }` (groups draw the digraph brackets).
  - `word_builder`: `{ "sound_boxes": [{"width":"single|digraph"}], "tiles": ["h","o","p","e","b","d"] }` (needed letters + distractors, order shuffled server-side).
  - `word_sort`: `{ "buckets": [{"id","label","emoji","examples":[]}], "chip": "hope" }`.
  - `phrase_dictation`: `{ "words": ["the","red","hen"] }`.
  - …one sub-schema per remaining type, all under `payload`.
- **`contract_version`** is an integer; a breaking change bumps it and the frontend registry + agent tool schemas are regenerated from the same schema file. Additive fields don't bump.

**Answer submission (the return leg):**
```json
POST /api/session/answer
{ "item_id": "uuid", "attempt": "hoap", "phase": "first" | "retry", "replays": 2 }
→ { "correct": false, "stars": 0, "tags": ["vowel_substitution"],
    "reveal": { "target":"hope", "markers":[...], "why":"…", "audio":"hope" },
    "next": "retry" }
```

**The agent's tool schemas are GENERATED from this file**, not hand-written — one tool per exercise `type` whose parameters = that type's payload sub-schema. This is what makes ADR-002's "agent output is guaranteed renderable" true by construction.

## Alternatives rejected
- **Per-type ad-hoc JSON, no schema** — fastest to start, but guarantees drift across the three consumers and makes agent output unvalidatable. The whole point of the registry is one shape.
- **Client-side grading** (send the answer key to the browser) — simpler round-trips, but puts the source of truth in an untrusted, inspectable client and breaks the stateless-server-authoritative model (ADR-004); a curious kid seeing answers in devtools is also a real classroom-software failure.
- **No version field** — costs one integer now; retrofitting versioning after data/agent prompts exist is painful.

## Consequences
- **Makes easy:** parallel building (frontend, API, agent authored independently against the frozen schema); one place to add exercise type #11.
- **Makes hard / costs:** upfront schema authoring before any exercise ships; discipline that nothing bypasses validation.
- **Follow-ups:** write `exercise.schema.json` as the first artifact of B6; a tiny schema-validation helper both API and agent import; a codegen (or manual mirror + test) for the agent tool schemas.
- **Risks accepted:** the schema will need additive evolution as later exercise types reveal gaps — the version field + additive rule absorbs that.
