# ONBOARDING — Spell Quest: Living State & Cold-Start Brief

> **The first thing any human or agent reads.** It always reflects the *current* reality so anyone can cold-start without prior context. **Stale state here is a bug** — update it at the end of every act.
> **Last updated:** 2026-07-07 · **Last session:** Installed the dev harness (constitution, running files, SOPs, ADRs 001–003 locked), converted the plan to a single AI-from-the-start phase (DeepSeek), and wrote `DESIGN_BRIEF.md` for Claude Design. Next: owner takes the brief to Claude Design; meanwhile the backend skeleton can start.

## 1. What this is (stable)
Spell Quest is a local web app that teaches spelling to the owner's 7-year-old daughter (dyslexic, dysgraphic, ADHD; ~1st-grade spelling level, entering 3rd grade). It runs Orton-Gillingham-style structured literacy as software: a 14-skill mastery model with decay ("rose of winds"), an adaptive selector targeting ~80% success, ~10 exercise types, a strict wrong-spelling correction routine, and an AI teacher-agent (DeepSeek) that plans sessions, explains errors in kid language, and keeps a teacher notebook. Gamified (stars, levels, creature collection, beat-your-own-record) with a radically simple dyslexia/ADHD-safe UI. Full product spec: `PLAN.md`.

## 2. Reading order (stable)
`CLAUDE.md` → this file → `docs/adr/README.md` → `docs/feature-catalog.md` → `docs/runner.md` → then per task: `PLAN.md` (pedagogy + product), `docs/architecture.md`, `DESIGN_BRIEF.md` (UI spec), `docs/sops/*`.

## 3. Architecture at a glance (stable-ish)
Browser (vanilla JS component registry + token CSS + browser TTS) ⇄ Flask API ⇄ `engine/` (deterministic: skills/selector/classifier/session/rewards) ⇄ `data/` (file JSON DB) · `agent/` (DeepSeek teacher: session planning, kid-voice feedback, memory notebook) sits behind the engine with graceful fallback when offline. See `docs/architecture.md`, ADR-001/002/003.

## 4. Current status (VOLATILE — keep current)
- Harness installed; repo initialized; nothing built yet — no `app.py`, no `engine/`, no UI.
- Product plan locked in `PLAN.md` (single phase, AI from the start; agent = DeepSeek, stubbed until the owner provides the key).
- `DESIGN_BRIEF.md` written — the input for Claude Design mockups (owner action).
- No `.env` / no DeepSeek key yet (`STUB:DEEPSEEK` until provided).

## 5. Decided vs. open (VOLATILE)
- **Decided / locked:** ADR-001 (Flask + file-JSON DB, atomic writes), ADR-002 (DeepSeek as the teacher-agent LLM, engine-fallback contract), ADR-003 (UI stack: token CSS + vanilla JS, no framework). Product/pedagogy spec = `PLAN.md`. Single build phase, AI wired from the start.
- **Open questions:**
  1. Which browser will the child use? (determines the TTS voice to tune for) — owner.
  2. Child's UI language/accent for TTS (US/UK English) — owner.
  3. Does the owner want the parent dashboard password-gated from the child? — owner.

## 6. Active milestone (VOLATILE)
**Wave 1 — Foundation:** design brief → Claude Design mockups → token-lock → backend skeleton (storage, skill model, selector, classifier, session API) + UI shell + first three exercise types (`word_builder`, `letter_boxes`, `echo_dictation`) + DeepSeek agent module with engine fallback. Live tracker: `docs/runner.md`.

## 7. How to work here (stable)
- Setup: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt` *(requirements.txt not created yet)*.
- Run: `flask --app app run --debug` → http://127.0.0.1:5000.
- Test: `pytest --cov` (coverage 80–100% on changed code; top of band for `engine/`).
- Secrets: `DEEPSEEK_API_KEY` in gitignored `.env` only.
- DoD: `CLAUDE.md` §✅. UI work: read `docs/sops/ui-development-guardrails.md` first. Gotcha: TTS voices differ per browser — verify dictation in the child's actual browser.

## 8. Session log (append-only, NEWEST FIRST)
- **2026-07-07 (act-002)** — Adopted the dev_harness: instantiated CLAUDE.md/CONVENTIONS.md/CHEAT-SHEET.md, all running files, SOPs, CI-gates doc; locked ADR-001/002/003; updated PLAN.md to a single AI-from-start phase with DeepSeek; wrote DESIGN_BRIEF.md for Claude Design. No code yet, so no tests/gates to run. Initial commit.
- **2026-07-07 (act-001)** — Wrote `PLAN.md`: pedagogy (why her errors happen, OG principles), 14-skill rose-of-winds model, 10 exercise types, error classifier, architecture (Flask + file DB + AI agent), kid-UI rules, gamification. Owner corrections captured: one phase, AI from the start, DeepSeek APIs.

> **Maintenance rule:** append a §8 line and refresh §4/§5/§6 at the end of **every** act, before yielding. Stable sections (§1–§3, §7) change rarely.
