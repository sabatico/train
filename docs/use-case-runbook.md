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

### KID-DAILY — the daily loop (browser manual-test script, verified act-012)
**As the child, I want to do today's practice and earn stars.**
1. `.venv/bin/python app.py` (or preview) → open `/app`.
2. ✔ Home: cream page, greeting, big pink **Start!**, mascot. Tap Start.
3. ✔ Teach card (yellow): today's pattern word + one rule sentence + 🔊. Tap **Got it!**.
4. ✔ Progress dots row appears; first exercise renders (a `word_builder` while skills are low — dashed sound boxes + letter tiles, or `letter_boxes`/`echo_dictation` as mastery rises). 🔊 speaks the word.
5. Answer wrong once → ✔ correction overlay: amber card, the **correct** word large with the pattern letters highlighted, a kid-voice why (agent when `SPELLQUEST_AGENT_LIVE=1`, else canned) + 🔊; type it correctly → advances. **Invariant check:** your wrong spelling is never shown.
6. Finish all items → ✔ reward screen: ⭐ count, level, hatch tease. `data/students/default/` now has an updated `skills.json`, a session log, and a `memory.md` note.

## Golden end-to-end paths (the flows to demo / regression-test)
- **Daily loop (primary):** KID-DAILY above — verified in-browser act-012 (home→teach→exercises→correction→reward reaches ⭐).
- **Agent-down path (must stay green):** same loop with `SPELLQUEST_AGENT_LIVE` unset (default) → runs fully on engine fallback (canned why lines); the child notices nothing. This is the default/tested path.

> Stories are added/fleshed out with real steps in the same slice that ships the feature (part of Done).
