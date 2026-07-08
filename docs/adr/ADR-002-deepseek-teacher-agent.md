# ADR-002 — DeepSeek API as the teacher-agent LLM, with a mandatory deterministic fallback

**Status:** Accepted
**Date:** 2026-07-07 · **Related:** `PLAN.md` §5, `docs/third-party-services.md`, invariant #2/#3 in `CLAUDE.md`

## Context
The product needs an LLM "teacher brain": plan each session from the skill state + teacher notebook, phrase corrections in 7-year-old-friendly language referencing HER specific error, review free writing gently, and write weekly parent notes. The owner decided the provider: **DeepSeek APIs, owner-supplied** (correction round CR1, 2026-07-07). AI is wired in from the start — but the key arrives after the UI + backend exist, and a 7-year-old with ADHD cannot wait out a slow or failing API mid-session.

## Decision
Use the DeepSeek chat-completions API (OpenAI-compatible, model `deepseek-chat`, function-calling) as the sole LLM, called from one module: `agent/teacher.py`. Hard rules:
1. **The deterministic engine must always be able to run a complete session alone.** Every agent call has a tight timeout (~10s session-plan, ~5s feedback) and a canned engine fallback; failures log `agent_fallback` and the child notices nothing.
2. **Agent output enters the app only through the exercise/feedback JSON contracts** (the same tool schemas the frontend registry renders) — validated before use; invalid output = fallback.
3. **No child PII in any prompt** (invariant #2): words, skill IDs, mastery numbers, error tags, notebook observations only; the child is "the student".
4. Until the key exists: `STUB:DEEPSEEK` — a mocked client with recorded-shape responses; live wiring + prompt tuning happen in the slice where the key lands (TBD-001).

## Alternatives rejected
- **Claude / OpenAI APIs** — capable, but the owner chose DeepSeek and supplies that account; cost at daily-kid-session volume is negligible on DeepSeek. Fallback: the client is OpenAI-compatible, so swapping providers later is a base-URL + model-name change behind `teacher.py`.
- **Local LLM (Ollama etc.)** — no API cost and fully private, but quality/consistency for pedagogy-critical kid-facing language is not there, and it adds heavy setup on the family Mac.
- **No LLM (pure rule engine)** — the engine alone is a decent trainer, but personalized explanations, session narratives and the teacher notebook are the product's core differentiator; the owner explicitly wants AI from the start.

## Consequences
- **Makes easy:** provider swap (OpenAI-compatible seam); building/testing everything now with the mocked client; cheap daily operation.
- **Makes hard / costs:** prompt quality can only be truly tuned once the key lands; DeepSeek function-calling quirks may need output-validation hardening.
- **Follow-ups:** freeze the exercise JSON contract early (it is also the tool-schema contract); TBD-001 resurfaces on key arrival.
- **Risks accepted:** dependence on an external API for the "rich" experience — bounded by rule 1 (the app never breaks without it).
