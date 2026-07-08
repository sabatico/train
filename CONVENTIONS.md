# Conventions — Spell Quest

How we write code and docs here, so a swarm of agents (and humans) produce one coherent codebase. These are the *authoring* rules; the *process* rules are in `CLAUDE.md` + `docs/sops/`.

## Doc authoring
1. **Explain WHY, not just what.** Every non-trivial decision in a doc states the reasoning and the **alternatives considered + why they lost.** A doc that only says "we do X" is half a doc. (Decisions of consequence graduate to an ADR.)
2. **Give a fallback.** When you recommend an approach, note the backup if it doesn't pan out.
3. **Living docs are dated + owned.** Headers carry "Last updated" and a one-line "what changed." Stale = a bug.
4. **Write for a cold start.** Assume the reader has zero prior context (because the next session's agent does).
5. **Pedagogical claims cite the plan.** Anything about *how the child learns* traces back to `PLAN.md` §1 (the pedagogy) — don't invent new teaching behavior in a code comment.

## Code authoring
1. **Match the surrounding code.** Comment density, naming, idioms, error handling — read the neighbors before you write. Consistency beats personal preference.
2. **Buildability by agents is a top-tier concern.** Prefer the most-trained, least-hallucinated, fewest-version-pitfalls option a cheaper builder model can't get subtly wrong. Novelty is a cost, not a feature. (This is why: plain Flask, vanilla JS, no frontend framework, no ORM.)
3. **Every dependency is paid for** in supply-chain + audit + maintenance surface. Don't add one to save a few lines. Target: Flask + pytest + an HTTP client for DeepSeek, little else.
4. **Make the unfinished visible.** Intentional gaps get a marker (`DEFERRED-TEST:`, `STUB:NAME`, `TBD:`, `TBD-UI:`) + a registry row + a CI check — never a silent shortcut.
5. **Errors and outcomes are observable; secrets are not.** Log meaningful outcomes (session built, answer classified, skill updated, agent call ok/failed+fallback); never log `DEEPSEEK_API_KEY` or child PII.
6. **Small, reviewable slices.** A change should be reviewable as one coherent unit.
7. **All `data/` writes go through one storage module** (atomic tmp-file + rename). No `open(..., "w")` on data files anywhere else — this is what makes invariant #1 testable.

## Commits & branches
- Trunk-based, direct to `master` on `origin` (`github.com/sabatico/train`), push at end of act — standing owner permission, no per-push approval. No force-pushes or history rewrites of pushed commits.
- Commit messages: imperative subject, a body that says *why* for anything non-obvious. Special prefixes the harness uses: **`quality-review:`** (a review baseline).
- Trailer on every commit: `Co-Authored-By: Claude <noreply@anthropic.com>`.

## Naming
- **Python:** modules/functions `snake_case`; one module per engine concern (`engine/skills.py`, `engine/selector.py`, …).
- **Skills:** stable snake_case IDs from `PLAN.md` §2 (`magic_e`, `letter_orientation`, …) — these are data contracts; never rename casually.
- **Exercise types:** stable snake_case IDs from `PLAN.md` §3 (`letter_boxes`, `word_builder`, …) — shared verbatim by backend payloads, frontend component registry, and agent tool schemas.
- **Feature-catalog IDs:** `KID-nn` (child-facing), `PAR-nn` (parent-facing), `CORE-nn` (modules). **Tickets:** `T-nnn`. **ADRs:** `ADR-nnn`, monotonic, never reused.
- **CSS:** design tokens `--sq-*` (e.g. `--sq-color-bg`, `--sq-space-4`); component classes `.sq-<component>`.

> Keep this short and real. A convention nobody follows is worse than none — prune the aspirational, keep the load-bearing.
