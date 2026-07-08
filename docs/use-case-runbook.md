# Use-Case Runbook — Spell Quest

> Every action a user can take, as **user stories with concrete, click/command-by-step instructions** + the expected result. Doubles as the **manual-test script** and the **how-to playbook**. Grounded in the *real* surfaces (routes, commands, buttons) — not invented. **Update changed flows + add a story for any new capability as part of Done.**
> **Legend per run:** ✅ pass · ❌ fail (defect) · ⚠️ partial/blocked.

## Before you start — environment realities
- Local only: `source .venv/bin/activate && flask --app app run --debug` → http://127.0.0.1:5000. *(Nothing runnable yet — this runbook fills in as slices land.)*
- DeepSeek is `STUB:DEEPSEEK` until the key lands in `.env`; agent-dependent flows run on the deterministic engine fallback — feedback text will be the canned per-rule lines, and that is the *expected* stubbed behavior, not a defect.
- To simulate skill states (e.g. "magic_e is weakest"), edit `data/skills.json` while the server is stopped — never mid-session.
- Dictation stories require speakers on and a browser with `speechSynthesis` voices installed.

## The child (the learner)
### KID-01 — Start a daily session
**As the child, I want to start today's practice so that I keep my streak and earn stars.**
*(⬜ planned — steps to be grounded in the real UI when KID-01 ships. Expected shape:)*
1. Open http://127.0.0.1:5000 → home shows avatar greeting, streak flame, one big "Start" button.
2. Tap Start.
3. ✔ Expect: session screen with 8–12 progress dots; first item is a warm-up from a mastered skill.

### KID-14 — The correction routine (the invariant flow)
**As the child, when I spell a word wrong, I want gentle help so that I learn the rule instead of feeling bad.**
*(⬜ planned. Expected shape — this is also the guardrail manual check:)*
1. In any exercise, type a wrong spelling (e.g. `luv` for *love*) and submit.
2. ✔ Expect: soft "almost!", the attempt **disappears**, the correct word appears large with the pattern highlighted + a one-line why.
3. Retype the word correctly.
4. ✔ Expect: ✅ + 1 star (not 0), next item. **Invariant check:** the wrong spelling is nowhere on screen or in later screens; no earned star was removed.

## The parent (the owner)
### PAR-01 — Check the rose of winds
**As the parent, I want to see the skill radar so that I know what she's strong and weak in.**
*(⬜ planned.)*
1. Open http://127.0.0.1:5000/parent.
2. ✔ Expect: 14-axis radar chart matching `data/skills.json` mastery values; weakest skill named under it.

## Golden end-to-end paths (the flows to demo / regression-test)
- **Daily loop (primary):** KID-01 → KID-02 warm-up → KID-03 teach card → KID-04/05/10 practice items incl. one KID-14 correction → KID-15 reward chest → skills.json updated, session log written, ONBOARDING untouched.
- **Agent-down path (must stay green):** same daily loop with no/invalid `DEEPSEEK_API_KEY` → session runs fully on engine fallback; a `agent_fallback` line appears in the app log; the child notices nothing.

> Stories are added/fleshed out with real steps in the same slice that ships the feature (part of Done).
