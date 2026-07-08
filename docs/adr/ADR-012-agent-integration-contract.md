# ADR-012 — Agent integration contract (tool-use, prompt/PII boundary, caching, fallback wiring)

**Status:** Accepted *(2026-07-07; frozen before B8 — the agent module)*
**Date:** 2026-07-07 · **Related:** ADR-002 (DeepSeek + fallback), ADR-005 (tool schemas = exercise schemas), ADR-008 (tags), invariant #2 (no child PII), `PLAN.md` §5

## Context
ADR-002 chose DeepSeek and the "engine always works without it" rule. This ADR fixes the *implementation boundary*: exactly what the agent is called for, what goes into a prompt (invariant #2: no child PII), how its output is constrained (ADR-005 schemas), how failures fall back, and how we keep cost/latency sane for a daily kid session. Without this frozen, the agent module (B8) and the PII/security boundary are undefined.

## Decision

**Three call sites, each with a deterministic fallback (ADR-002):**
1. **Session plan** (1 call per session start, ADR-009): input = the skill state, the 60/30/10 slots the selector computed, and the `memory.md` notebook; the agent uses **tool-use where each tool = one exercise `type`** (schemas generated from ADR-005) to emit the item list + the teach-card copy + per-item `why` lines. Timeout ~10s → fallback = the deterministic selector's own plan with canned teach copy.
2. **Correction feedback** (on a miss, ADR-009 answer step): input = target, the classifier tags (ADR-008), the rule id; output = one 7-year-old-friendly sentence for `reveal.why`. Timeout ~5s → fallback = the canned per-rule line already on the item. May be pre-warmed during the item to hide latency.
3. **Sentence review + weekly note** (`sentence_scribe`, and end-of-session): gentle, praise-first, ≤2 corrections (PLAN §3/§9); appends a dated observation to `memory.md`. Failure → skip silently (no review shown is better than a stuck child).

**The PII boundary (invariant #2 — a hard, tested rule):** prompts are assembled by dedicated builders in `agent/prompts/` that accept ONLY: words, skill ids + mastery numbers, error tags, rule ids, and prior `memory.md` notes. The child is referred to as "the student". `display_name`, avatar, age, and any free-typed sentence content beyond what's needed for review are never placed in a prompt. A guardrail test feeds a profile with a name and asserts it never appears in any built prompt. (For `sentence_scribe`, her writing IS the input to review — that text is sent, but it is task content, not identity PII; the boundary test still asserts no name/profile leakage.)

**Output validation:** every agent response is validated against the ADR-005 schema (plans) or a length/format check (feedback) before use; invalid → fallback + a logged `agent_reject`. The served model can shift under the `deepseek-chat` alias (third-party-services note), so validation is load-bearing, not optional.

**Caching / cost:** teach-card copy and `why` lines are cached per `(rule_id, skill_id)` in `data/students/<id>/agent_cache.json` so repeated patterns don't re-bill; expected spend stays < $2/mo (third-party-services). One `agent/client.py` wraps the OpenAI-compatible HTTP call (base URL + model + key from `.env`), so a provider swap is one module.

**Observability:** log `agent_ok` / `agent_fallback` / `agent_reject` with latency and which call site — never the key, never child PII.

## Alternatives rejected
- **Agent drives the whole session (picks items, grades, scores)** — maximal "AI", but non-deterministic, unauditable, can't run offline, and would let a bad response teach the child wrong. The deterministic engine owns pedagogy; the agent adds language and ordering. This is the ADR-002 line, made concrete.
- **Free-form agent output parsed leniently** — brittle; tool-use + schema validation is what makes "guaranteed renderable" real.
- **No caching** — simplest, but re-bills identical teach/why text daily; the cache is cheap and keeps cost negligible.
- **Send full profile for "personalization"** — violates invariant #2 for marginal gain; the notebook already carries the useful, non-identifying personalization ("responds well to the bodyguard-e story").

## Consequences
- **Makes easy:** a testable PII boundary; provider swap (one client module); cost control; the app never stalls on the API (every site has a fallback).
- **Makes hard / costs:** prompt tuning needs real DeepSeek responses (the key is live — do it during B8); maintaining the tool-schema mirror of ADR-005 (generate + test it).
- **Follow-ups:** `agent/prompts/` builders + the PII guardrail test; `agent_cache.json` schema (ADR-006 addendum); pre-warm strategy for feedback latency.
- **Risks accepted:** DeepSeek quality/latency variance — bounded entirely by the fallbacks; worst case the app runs as the (already complete) deterministic trainer.
