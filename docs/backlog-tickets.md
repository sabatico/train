# Backlog — Issue & Feature Tickets — Spell Quest

> **The queue of work to do** — bugs to fix and features to build that are **not yet in an active wave.** This is *not* the active-wave runner (`runner.md` = what's in flight right now); this is the prioritized pile the next wave is drawn from. A ticket moves **here → into a runner** when a wave picks it up, and **→ done** when shipped.
> **Distinct from `tbd-parking-lot.md`:** here = "we intend to do this, just not scheduled yet." There = "we *deliberately deferred* this because a constraint blocks it."

**Type:** 🐞 bug · ✨ feature · 🧹 chore/tech-debt · 📈 improvement
**Priority:** P0 (now) · P1 (next) · P2 (soon) · P3 (someday)
**Status:** ☐ open · ▶ scheduled (in a wave) · ✅ done · ✖ won't-do

| ID | Type | Pri | Title | Description / acceptance | Status | Source |
|----|------|-----|-------|--------------------------|--------|--------|
| T-001 | ✨ | P1 | Remaining exercise types beyond Wave 1's three | `missing_letters`, `bd_ninja`, `word_sort`, `heart_word_spotlight`, `phrase_dictation`, `beat_yesterday` (KID-06..09, 11, 13); done when each renders from the registry + has a runbook story | ☐ | PLAN §3 |
| T-002 | ✨ | P1 | `sentence_scribe` free writing + gentle AI review (KID-12) | Max 2 corrections per text, praise-first; needs live agent | ☐ | PLAN §3 |
| T-003 | ✨ | P1 | Parent dashboard: radar chart + error log + settings (PAR-01/02/04) | Radar matches skills.json; settings persist to profile.json | ✅ | done act-013 (v1); notebook viewer + weekly note still open (T-004) |
| T-004 | ✨ | P2 | Weekly agent parent-note generation (PAR-03) | Appended to data/memory.md, readable on dashboard | ☐ | PLAN §5 |
| T-005 | ✨ | P2 | Word banks: vowel_teams, r_controlled, suffixes, doubling_endings | Same schema as Wave 1 banks; owner reviews word choice | ☐ | PLAN §2 |
| T-006 | ✨ | P2 | Streak freeze token + level-up celebration screen (KID-15/17 polish) | Missing a day with a token keeps the flame; never punitive | ☐ | PLAN §6 |
| T-007 | 📈 | P3 | Pre-generated natural-voice audio to replace browser TTS | Only if browser voices prove too robotic for the child | ☐ | PLAN §5 |
| T-008 | 🧹 | P2 | CI gate scripts (secret-scan, marker registries, no-inline-styles lint, coverage floor) as local pre-commit/`make gates` | Per `docs/ci/gates.md`, adapted to a no-remote local repo | ☐ | harness |
| T-009 | ✨ | P3 | "Paper mode" — child writes on paper first, then types what she wrote | Dysgraphia bridge; PLAN §9 | ☐ | PLAN §9 |
| T-010 | 🧹 | P2 | Automated JS unit tests for the UI (`static/js/*`) | Needs a JS test harness (vitest/jsdom) — a dependency+ADR decision. Until then UI is browser/manual-verified (use-case-runbook). Cover: registry rendering, correction overlay, session loop, speech wrapper | ☐ | act-012 (B7 DoD gap) |
| T-011 | 🧹 | P2 | Self-host the Lexend font (woff2 in `static/fonts/`) | Currently falls back to system-ui via the token stack; self-hosting delivers the dyslexia-friendly typeface with zero external requests (third-party-services) | ☐ | act-012 |
| T-012 | ✨ | P2 | Agent session-plan / teach-copy enrichment | ADR-012 call site #1: agent reorders the plan + writes teach-card copy via tool-use. Feedback (#2) already wired; this is #1 | ☐ | ADR-012 |
| T-013 | 📈 | P3 | Home streak flame + mission chip; reward chest/confetti/level-up polish | DESIGN_BRIEF §1/§4 — richer home + reward moments beyond the functional versions | ☐ | act-012 |

> **Definition of Ready** (before a ticket can be pulled into a wave): clear acceptance criteria, no unresolved blocking decision (else it belongs in `tbd-parking-lot.md` or as an open question in ONBOARDING §5), and a rough size. Keep this list groomed — prune `✅`/`✖` periodically into the session log.
