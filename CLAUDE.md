# CLAUDE.md — Spell Quest (read this first, every session)

This repo holds **Spell Quest** — an adaptive spelling web app for the owner's 7-year-old daughter, who has dyslexia, dysgraphia and ADHD. It teaches spelling via Orton-Gillingham-style structured literacy: a 14-skill mastery model ("rose of winds"), adaptive exercise selection, an AI teacher-agent (DeepSeek API) with persistent memory, and a gamified, distraction-free kid UI. Full product design: `PLAN.md`.
Led by an AI lead agent + spawned role sub-agents; the human owner (the parent) gives final acceptance.

## 🧭 COLD START — read these IN ORDER for full context (do not skip)
1. **`docs/ONBOARDING.md`** — **ALWAYS FIRST.** The living state doc: current status, decided-vs-open, the active milestone, and the append-only session log (newest first). It always reflects *current* reality — trust it over older docs.
2. **`docs/adr/README.md`** — the **ADR log** (the running list of locked decisions). Never re-litigate a locked decision.
3. **`docs/feature-catalog.md`** — the **single inventory of EVERYTHING** the product does (every user-facing capability + every core module), with status, surface, tests. The fastest "what does this do, end to end?" answer.
4. **`docs/runner.md`** — the **live tracker for the active work wave** (what's in flight, statuses, open questions).
5. Then dive deeper as the task needs — `docs/architecture.md`, `PLAN.md` (the pedagogy + product spec), the relevant ADRs, `docs/sops/*`. **Touching pedagogy/exercise logic?** read `PLAN.md` §1–§4 first — the teaching rules there are product invariants. **Doing UI work?** read **`docs/sops/ui-development-guardrails.md`** FIRST (tokens + components, zero inline styles). **Implementing a design mockup pixel-perfect?** read **`docs/sops/mockup-implementation.md`** (structure preservation + extract values + rendered-HTML diff; ask for the structured handoff — the styling-context manifest is `DESIGN_BRIEF.md` §9). **Touching an integration?** read **`docs/third-party-services.md`** first.
6. Work-to-do lives in **`docs/backlog-tickets.md`** (bugs + features, unscheduled); work deliberately deferred-by-constraint lives in **`docs/tbd-parking-lot.md`**.

## ⛔ Standing rules (non-negotiable — never miss these)

- **NEVER run a destructive / irreversible action** (delete/drop/destroy/`rm -rf`/force-push/teardown of real resources, deleting or rewriting files under `data/`, etc.) **without first explaining exactly what it removes + the blast radius AND getting explicit owner approval.** Prefer reversible/targeted alternatives. Approval in one context does not extend to the next.
- **Invariants are sacred:**
  1. **No child data loss** — `data/` is the child's learning history; all writes are atomic (tmp-file + rename); nothing under `data/` is deleted or bulk-rewritten without owner approval.
  2. **No child PII to external services** — API calls to the AI provider carry words, skill states and error patterns only; never the child's name, age, or any identifying detail.
  3. **The pedagogical safety rules never break:** a wrong spelling is never persisted into UI state or redisplayed after the correction routine; feedback is never punitive (no red X walls, no losing earned stars); no visible timers outside opt-in game exercises.

  The **guardrail test suite** that protects these is **owner-owned** — builders must pass it, never weaken or delete it.
- **No secrets in chat/docs/commits.** Credentials live in the gitignored `.env`. **Never send secrets/keys/tokens/real child data to any external model or service.** Code/specs only.
- **Model / role policy (owner-set, 2026-07-07):**
  - **Builders & test authors: Sonnet 5 and DeepSeek.** Cross-authorship still holds — the builder writes ZERO tests for its own code (see `docs/sops/test-and-coverage.md`); pair them (Sonnet builds → DeepSeek tests, or vice versa). *Practical note:* DeepSeek is not a native subagent model in this environment — until the `DEEPSEEK_API_KEY` lands and a small test-author script wraps its API, cross-authorship = a **separate fresh Sonnet agent instance**; switch to the Sonnet↔DeepSeek pairing once the key exists.
  - **Opus 4.8: the judge.** Runs quality reviews (`docs/sops/quality-review.md`), verifies "it actually works" claims, and reviews risky slices before merge. Builders never grade their own homework; Opus does.
  - **Escalation ladder (the lead's standing duty):** watch where builder agents fail. **Two failed attempts by Sonnet/DeepSeek on the same slice → escalate that slice to Opus. Opus also failing, or the problem is pedagogy-critical/architectural → the lead (Fable) takes it inline.** Never let a builder grind out a third failing attempt; escalating late wastes more than the stronger model costs.
  - **Max context to every spawned agent.** Skimpy prompts cause most agent mistakes: every spawn gets the full relevant context — the frozen contract, the actual file contents it must match, `PLAN.md`/`DESIGN_BRIEF.md` excerpts that govern the slice, an existing exemplar (e.g. a neighboring module or test file), the invariants, and the DoD. Don't summarize what you can paste.
  - A **scribe** (cheap model or the lead inline) documents each finished item into the running files.
- **Coverage is part of Done:** every slice **measures** coverage on its new/changed code (`pytest --cov`) and hits **80–100%** (top of the band for `engine/` — it drives what the child is taught). A test you can't write yet (missing harness/dep) is **DEFERRED, never dropped** — tag the site `DEFERRED-TEST:`, register it, and write it the moment the dependency lands.
- **Git:** remote = `https://github.com/sabatico/train.git`; trunk-based, **commit and push directly to `master`** — owner approval is NOT needed for commits/pushes (owner-granted 2026-07-07). Push at the end of every act. (The destructive-action rule still applies in full: no force-push, no history rewrites of pushed commits, no deletions without approval.) End commits with: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- **Spend:** sub-$5 de-risk validation (e.g. a DeepSeek API probe) is never a blocker — just do it, then clean up (per the destructive-action rule).
- **"Quality review" = run the SOP (`docs/sops/quality-review.md`):** review ALL code since the last `quality-review:` commit across 3 axes (code quality / tests+coverage / observability); lead leads + an **independent second reviewer**; lead **judges** each finding; resolve; verify green; commit with the `quality-review:` prefix.
- **Maintain state — no stale docs (check at the end of EVERY act, before yielding):** update ALL of these "running files" for anything the work changed (mandatory, exactly like ONBOARDING — don't wait for "session end"):
  - **`docs/ONBOARDING.md`** — status + decided/open + milestone + a session-log line.
  - **`docs/runner.md`** (the active wave runner) — flip every touched item's status + add new items.
  - **`docs/feature-catalog.md`** — flip the status / add the row for any capability added/changed/removed.
  - **`docs/use-case-runbook.md`** — update changed flows + add a story for any new capability.
  - **`docs/build-tracker.md`** — reflect progress.
  - *(if touched)* **`docs/backlog-tickets.md`** (move/close tickets), **`docs/tbd-parking-lot.md`** (add deferrals + fire resurface triggers), **`docs/third-party-services.md`** (new/changed integration).

## ✅ Definition of Done (a slice is not done until ALL are true)
1. It works (the happy path + the obvious edges).
2. Tests authored by a different role/model, measured to the coverage target (or deferred-and-registered).
3. Build + tests + **all gates** green — *watched*, not assumed.
4. Observability: meaningful outcomes are logged/traced; no secret material or child PII in logs.
5. Decisions of consequence recorded as ADRs; running files updated.
6. Committed with a clear message.

## 🔑 Quick facts
- **Repo / access:** `~/Documents/Personal/CodingProjects/train` → `origin` = `https://github.com/sabatico/train.git`, branch `master`; the agent has full local access + standing push permission; owner runs the app on this Mac.
- **Stack:** Python 3 / Flask · vanilla JS + CSS-custom-property tokens frontend (no framework — ADR-003) · file-based JSON database under `data/` (ADR-001) · DeepSeek API for the teacher agent (ADR-002) · browser `speechSynthesis` for TTS.
- **Environments:** dev = prod = this machine. The only real environment is the child's daily use — `data/` is production data from the first real session onward.
- **Toolchains & non-obvious knobs:** Python via `python3`; venv at `.venv/`; run `flask --app app run --debug`; tests `pytest --cov`. TTS quality differs per browser — test dictation in the browser the child actually uses (Safari and Chrome voices differ).
- **Secrets by NAME (never values):** `DEEPSEEK_API_KEY` → `.env` (gitignored). That is the only secret.
- **Phase:** pre-build. Harness installed; product plan locked (`PLAN.md`); next: UI design brief → Claude Design mockups → build UI + backend → connect DeepSeek agent. Single continuous phase — AI wired in from the start (stubbed until the key is provided).
