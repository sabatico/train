# Architecture Overview — Spell Quest

> The big-picture map of the system: the major components, how they connect, where the data/control flows, and the boundaries that matter. Deep specifics live in their own docs + ADRs; this is the **one diagram + one page** that orients anyone before they go deeper. Update when a structural boundary changes.

## 1. The shape (one diagram)
```
 browser (child / parent)
 ├─ UI shell + component registry (vanilla JS, one renderer per exercise type)
 ├─ tokens.css (--sq-*)  +  scoped component CSS        [ADR-003]
 └─ speechSynthesis TTS (dictation audio, local)
        │  JSON over HTTP (the frozen exercise contract: {type, payload})
        ▼
 app.py — Flask API (session start / next item / submit answer / skills / settings)
        ▼
 engine/  — DETERMINISTIC CORE (always able to run a full session alone)
 ├─ store.py      ← ALL data/ I/O, atomic writes          [invariant #1]
 ├─ skills.py     ← mastery EMA + decay + prerequisite gates
 ├─ selector.py   ← 60/30/10 adaptive pick + step-down ladder
 ├─ classifier.py ← attempt vs target → error tags → skill signals
 ├─ session.py    ← warmup → teach → practice → challenge → reward
 └─ rewards.py    ← stars/streak/levels (never subtract)   [invariant #3]
        │ enrich (plan, kid-voice feedback, notebook) — OPTIONAL path
        ▼
 agent/teacher.py ──HTTPS──▶ DeepSeek API                  [ADR-002, STUB:DEEPSEEK]
   (tight timeouts; on any failure → engine's canned fallback; no child PII in
    prompts [invariant #2])
        ▼
 data/ — file-JSON DB [ADR-001]: profile, skills, word_bank/, sessions/, rewards,
         memory.md (the agent's teacher notebook)
```

## 2. Components
| Component | Responsibility | Tech | Lives in | Key ADRs |
|-----------|----------------|------|----------|----------|
| UI shell + registry | Render `{type,payload}` exercises; correction routine; reward screens | vanilla JS + token CSS + Jinja | `static/`, `templates/` | ADR-003 |
| Flask API | The HTTP seam between UI and engine; owns the exercise JSON contract | Flask | `app.py` | ADR-001 |
| Deterministic engine | Everything pedagogical that must work offline: skills, selection, classification, sessions, rewards | pure Python, heavy unit tests | `engine/` | ADR-001 |
| Teacher agent | LLM enrichment: session plans (via tool schemas = exercise types), kid-voice explanations, sentence review, memory notebook, parent notes | DeepSeek chat API, OpenAI-compatible client | `agent/` | ADR-002 |
| File DB | All state, human-readable JSON/MD, atomic writes | filesystem | `data/` | ADR-001 |

## 3. The boundaries that matter
- **Trust / security boundary:** localhost-only app; the real boundary is the **outbound DeepSeek call** — the only place data leaves the machine. Gate: `agent/teacher.py` prompt builders (words/skills/tags only — invariant #2). Untrusted input = the child's free-typed text; it goes to the classifier and (for `sentence_scribe`) to the agent, never into shell/eval/paths.
- **Stage-2 scale seams (ADR-004 — build rules NOW, even though multi-user is parked):** every `store.py` call carries `student_id` (constant `"default"` in v1); the API is stateless per request; routes are tenancy-shaped (`/app/*`, `/api/*`, `/parent/*`); the frontend stays WebView-clean with TTS behind `speech.js`.
- **Contract boundaries (the lead freezes these before parallel work):**
  1. **The exercise JSON contract** `{type, payload}` per exercise type — shared by API responses, the frontend registry, AND the agent's tool schemas. One schema, three consumers.
  2. **`store.py`'s API** — no other module touches `data/` files directly.
  3. **Skill + error-tag IDs** (PLAN §2/§4) — data contracts across engine, agent prompts, and stored history.
- **Data flow:** start session → engine builds plan (agent may refine) → UI renders item-by-item → each answer → classifier tags → skills.py updates mastery → store.py persists → end of session → rewards + session log + (agent) notebook append.

## 4. Cross-cutting
- **Config & environments:** one env (the family Mac). `.env` for `DEEPSEEK_API_KEY`; `data/profile.json` for user-visible settings. External deps → `third-party-services.md`.
- **Observability:** stdlib `logging` to stderr + `data/logs/app.log`; log outcomes (session_built, answer_classified, skill_updated, agent_ok/agent_fallback) — never PII/secrets.
- **Build & deploy:** no build step; `flask run` locally; gates run locally per `docs/ci/gates.md` (T-008) since there is no remote CI yet.

## 5. Where to go deeper
`PLAN.md` (pedagogy + product spec — the WHY of every engine rule) · `DESIGN_BRIEF.md` (UI spec) · `docs/adr/` (locked decisions) · `docs/third-party-services.md` (DeepSeek wiring).
