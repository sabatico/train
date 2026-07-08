# DESIGN_BRIEF.md — Spell Quest UI (the handoff brief for Claude Design)

> **Audience of this document:** Claude Design (or any designer) producing high-fidelity
> mockups for Spell Quest. It describes every screen, every interaction, and the
> non-negotiable principles. §9 is the **styling-context manifest** — the output rules
> the design export must follow so we can implement it pixel-perfect
> (per `docs/sops/mockup-implementation.md`).
> **Last updated:** 2026-07-07 · initial version.

---

## 1. What you are designing

**Spell Quest** — a spelling-practice web app used daily (10–15 min) by **one 7-year-old
girl** with **dyslexia, dysgraphia and ADHD**, on a laptop/desktop browser at home, usually
with a parent nearby. She reads at ~1st-grade level. She loves being first, winning,
collecting things, and reaching new levels. There is also one **parent-facing dashboard**.

**The emotional brief (check every screen against this):**
> **Warm, playful, calm and safe — like a kind teacher's table, never like a test.**
> Cozy and encouraging, not loud and arcade-y. Mistakes must feel like a friendly
> "almost! let me show you" — never like failure.

**Personas / areas:** THE KID (everything in §4–§6) and THE PARENT (§7). The kid screens
are the product; the parent screens can be plainer.

---

## 2. Non-negotiable design principles (dyslexia + ADHD)

These are product invariants, not stylistic preferences. Every screen must pass all of them.

1. **One thing on screen at a time.** A single centered task card per screen. No sidebars,
   no persistent nav, no notification chrome, no decorative text blocks. ADHD design =
   remove, remove, remove.
2. **Typography:** a dyslexia-friendly font (**Lexend**; fallback OpenDyslexic). Kid-facing
   exercise text ≥ 28px (target words render 40–56px), letter-spacing ≈ 0.05em,
   line-height ≥ 1.6, **lowercase-first** presentation (b/d confusion lives in lowercase).
   Never italic, never ALL-CAPS for words she must read, never justified text.
3. **Background is warm cream (≈ #FAF6EE), never pure white** (glare/visual swimming),
   with near-black text. High contrast (WCAG AA minimum, aim AAA for word text). Never
   place text over images or gradients.
4. **A wrong spelling is never displayed** except for ~1s as it dissolves in the correction
   flow (§5). No screen, list, or summary ever shows her misspellings back to her.
5. **No visible timers, countdowns or clocks** anywhere — except inside the two opt-in
   game exercises (`bd_ninja`, `beat_yesterday`), and even there the pressure cue is a
   filling meter, not a ticking countdown clock.
6. **Nothing punitive, ever.** No red ✗ marks, no "wrong!", no score decreasing, no lost
   stars, no sad mascot. Error state color is a warm amber, never red. Feedback vocabulary:
   "almost!", "so close!", "let's look together".
7. **Audio is a first-class citizen.** Every dictated item has a big 🔊 replay button —
   unlimited replays, visually identical on the 10th press (no nagging).
8. **Motion is gentle and short** (200–400ms, ease-out). Celebrations may be big (confetti
   on level-up) but everything else animates subtly. No flashing, no shaking on errors,
   no autoplaying loops (respect `prefers-reduced-motion`).
9. **Touch targets ≥ 56px**; letter tiles and inputs are big and chunky. She may use a
   trackpad imprecisely.
10. **Reading load near zero.** Instructions are one short line + an icon + (ideally) auto-
    spoken. Buttons carry one word ("Go!", "Done", "Again") or just an icon.

---

## 3. Visual language & tokens (direction, not final values)

- **Palette:** warm cream page (#FAF6EE-ish); a deep friendly ink for text (#2B2B33-ish);
  ONE cheerful primary (candy coral or warm teal — designer's choice) for actions;
  soft amber for "almost"; leafy green for success; gold/yellow for stars; a handful of
  pastel accents for pattern buckets and collection creatures. Cards are slightly lighter/
  whiter than the page with soft shadows and large radii (16–24px) — chunky, rounded,
  storybook-like.
- **Type:** Lexend throughout (kid AND parent). Weights: regular/medium/semibold only.
- **Iconography:** rounded, filled, friendly; emoji-adjacent is fine (the product spec
  already uses ⭐ 🔊 ❤️ 🪄 🎁 🔥).
- **Mascot:** a small friendly creature (owl/fox/dragon — designer's choice) that greets,
  reacts happily to success, and looks *encouraging* (never disappointed) on misses.
  It appears in a consistent corner slot, small — it must never compete with the task.
- Name every value as a semantic token (`--sq-color-bg`, `--sq-color-ink`,
  `--sq-color-primary`, `--sq-color-success`, `--sq-color-almost`, `--sq-color-star`,
  `--sq-space-1..8`, `--sq-radius-card`, `--sq-font-display`…). See §9.

---

## 4. The kid screens

### S1 — Home / Welcome
**Purpose:** start today's session in one tap; feel greeted and pulled forward.
**Layout:** mascot greeting by name ("Hi Mia! Ready for today's quest?" — placeholder
name), streak flame with day count, today's mission line ("Today: magic e 🪄"), and ONE
huge primary button: **Start!** Below, two small, quiet secondary links as icon-chips:
**My Collection** (shelf icon) and **Games** (controller icon → `beat_yesterday` /
`bd_ninja` free play). Optionally the child's level badge (e.g. "Word Wizard, Lv. 4")
near the avatar.
**Interactions:** Start → S2 with a short "quest begins" transition. Everything else is
one tap deep. No settings, no logout, no clutter — parent stuff is NOT reachable from
kid screens (separate `/parent` URL).

### S2 — Session shell (wraps every exercise)
**Purpose:** the persistent frame all exercises render inside.
**Layout:** top edge: a row of **8–12 progress dots** — done dots become gold stars,
current dot gently pulses, upcoming dots are hollow. That row is the ONLY chrome.
Mascot small in a bottom corner. The center is the **task card** (one exercise, §6).
Bottom-right of the card: the primary action (**Done** / auto-advance). No back button
mid-item; a small, quiet "pause/exit" (parent-facing) icon top-right that asks
"Stop for today?" with Keep going / Stop options.
**States to design:** entering item (card slides in), answered-correct (stars fly to the
dot row), the correction overlay (§5), between-items breather (~600ms).

### S3 — Teach card (the mini-lesson, 1 per session)
**Purpose:** introduce/refresh the session's focus pattern as a tiny story, before practice.
**Layout:** a special-colored card. Big title with the pattern hero (e.g. "The Magic e 🪄"),
the rule as ONE sentence in kid language ("Magic e is silent — it makes the vowel say its
name!"), two example words with the pattern letters highlighted (hop → hope), a 🔊 button
that reads the card aloud, and **Got it!** to proceed. Design it swipeable/tappable as
2–3 tiny steps if that reads calmer than one card.

### S4 — Reward screen (end of session)
**Purpose:** the payoff; end every day on a win.
**Layout:** a treasure chest opens; stars fly out and count up into the total; a progress
bar fills toward the next level ("14 ⭐ to Word Wizard!"); if a pattern was mastered
today, a creature egg appears with "Something is hatching… come back tomorrow!" tease.
One button: **Yay! Done.** Confetti allowed here.
**Variants:** normal end · level-up (S4b: full-screen celebration, new level name/badge,
bigger confetti) · new-creature-hatched (S4c: the creature introduces itself, "Add to my
shelf!").

### S5 — Collection shelf
**Purpose:** make mastery visible and collectible; her trophy room.
**Layout:** a cozy wooden-shelf illustration; each mastered pattern = one creature/sticker
with its pattern label ("Sh-sh-shark — sh"); unmastered patterns = mysterious eggs with a
"?" (tappable: mascot says "Keep practicing to hatch this one!"). Total star count and
current level badge at top. Back arrow to Home.
**Interaction:** tapping a creature plays a tiny idle animation + speaks 2 example words
of its pattern.

---

## 5. The correction flow (design this as ONE reusable overlay — the most important
interaction in the product)

Trigger: any wrong answer in any exercise. Sequence (design each beat):

1. **Soft "almost"** (~1s): the card glows warm amber, mascot leans in encouragingly,
   text "Almost!" — the child's attempt **dissolves/fades away** (it is never shown again).
2. **The reveal:** the CORRECT word appears large (48px+), with the relevant pattern
   letters highlighted in the primary color (for heart words: the tricky letters get a
   small ❤️ above them). Under it, ONE short kid-voice line explaining why (comes from the
   backend, e.g. "love ends in silent e — the e is v's bodyguard 🛡️"), with a 🔊 that
   reads it aloud (design for auto-read once).
3. **Retype-it-right:** the same input the exercise used, empty, with the correct word
   still visible above as the model. She copies it correctly.
4. **Resolve:** gentle ✅ + ONE star (first-try answers earn two; corrected answers still
   earn one — design the star feedback so one star feels like a win, not a consolation).
   Overlay closes, next item.

**Never in this flow:** red, ✗, "wrong", the misspelling, a disappointed mascot, any sound
harsher than a soft chime.

---

## 6. The exercise cards (all render inside S2's task card)

Design each as a variant of the task card. Common anatomy: *(a)* prompt zone (picture/
emoji + 🔊, or the visible word), *(b)* answer zone (the type-specific input), *(c)* the
one-word action button. Instruction line is icon + ≤5 words, auto-spoken.

**E1 — `word_builder` (tap tiles into boxes)** — scaffolding: high; used to introduce patterns.
Picture/emoji + 🔊 speaks the word. Below: empty **sound boxes** (one per phoneme —
digraphs like *sh* are ONE box, drawn slightly wider). Beneath: a tray of big letter
tiles (the needed letters + 2–3 distractors), shuffled. Tap a tile → it hops into the
next empty box; tap a placed tile → it returns to the tray. Wrong tile in a box is
allowed until she taps Done (no live nagging). Design: filled vs empty box states, the
tile hop animation, a two-letter tile (sh) visual.

**E2 — `letter_boxes` (type, one box per letter)** — the workhorse.
🔊 + picture. A row of **individual letter input boxes**; phoneme groups joined by a
colored underline bracket beneath (c·a·t = 3 separate; s+h share one bracket). Typing
auto-advances to the next box; backspace goes back. Boxes are huge (≥64px), letters
render ≥40px. Design: empty/focused/filled states, the phoneme brackets, on-screen
Done button (Enter also submits).

**E3 — `missing_letters` (cloze)**
The word displays large with 1–2 letters replaced by empty boxes (`l _ v e`), picture +
🔊 available. Only the gaps are editable. Focus jumps between gaps.

**E4 — `bd_ninja` (discrimination mini-game — one of the two timed screens)**
Intro card first: the mnemonic ("**b** has its belly in front — like a **b**at before the
**b**all ⚾") with a big b and d drawn with their anchor pictures; then the game: letters
float up gently (bubbles/balloons); "Pop only the **b**!" Tapping a correct one pops it
(+sparkle); tapping wrong just wobbles it (no penalty flash). Progress = a filling meter,
NOT a countdown clock. End = stars + "new record?" moment.

**E5 — `word_sort` (drag into buckets)**
Two (max three) big labeled buckets ("magic e 🪄" / "no magic e"); word chips appear one
at a time center-screen; she drags (or taps a bucket) to sort. Correct → chip settles in
with a chime; wrong → chip drifts back gently and the correct bucket glows as a hint.

**E6 — `heart_word_spotlight` (look–cover–write–check)**
Three beats on one card: **LOOK** — the word large, tricky letters marked with small ❤️
above, 🔊 speaks it, mascot points; **COVER** — she taps a big "Cover it!" flap that
slides over the word (satisfying physical feel); **WRITE** — letter_boxes-style input
from memory; **CHECK** — flap lifts, side-by-side confirm. Design the flap interaction.

**E7 — `echo_dictation` (hear → type)**
Minimal card: a big 🔊 (auto-plays once), an optional faded hint picture, ONE large free
input (single word), Done. The quietest screen in the app — pure recall.

**E8 — `phrase_dictation` (hear → type, per word)**
🔊 speaks a 2–4 word phrase ("the red hen"). Below: one input **per word**, sized to the
word, laid out like a sentence line. A small "🔊 word" ghost-button under each input
replays just that word. Design the visual grouping so the phrase reads as one line.

**E9 — `sentence_scribe` (free writing + gentle review)**
Prompt: a picture + 🔊 ("Write what the cat is doing"). A big friendly lined text area
(2–3 lines max). After submit: the **review card** — her sentence rendered CORRECTED
(never her raw errors), with up to 2 taught-pattern spots gently highlighted + one
praise line first ("Great sentence! Two little magic-e words to polish:") and the same
retype-right interaction per highlighted word. Design: praise-first hierarchy.

**E10 — `beat_yesterday` (record sprint — the second timed screen, opt-in from Home)**
Pre-screen: her current record big ("Your record: 7 words ⭐ — beat it?") + Go. In-game:
echo_dictation-style items back-to-back, a **word counter counting UP** (no clock; a
subtle filling meter is the only time cue). End: record beaten → trophy + confetti;
not beaten → "So close! 6 today — your record is still 7. Tomorrow!" (warm, zero shame).

---

## 7. Parent screens (plainer, denser is fine — same tokens, adult scale ~16–18px)

### P1 — Dashboard (`/parent`)
- **The Rose of Winds:** a 14-axis radar chart of skill mastery (the centerpiece), each
  axis labeled with a friendly skill name; a "weakest three" callout beneath.
- **This week:** sessions done, stars earned, streak, minutes practiced.
- **Teacher's notebook:** the AI agent's latest weekly note + a reverse-chron feed of
  its observations (rendered from markdown).
- **Error log:** a table of recent misses — date, target word, error type tag, skill —
  (misspellings ARE shown here; this surface is parent-only and never visible to the child).

### P2 — Settings (`/parent/settings`)
Session length (items per session), TTS voice + speed (with a "hear a sample" button),
font size toggle, child's display name + avatar/mascot choice, streak-freeze grant,
data export (copy of `data/`). Plain form, big Save.

**Navigation guard:** parent screens live on separate routes with no links from kid
screens. Design a simple "grown-ups only" interstitial (e.g. "hold the button for 3
seconds") — a soft gate, not security.

---

## 8. States the mockup must include (don't leave these to the implementer)

For each screen: default · focused/active input · correct-answer beat · the correction
overlay (§5) · loading (mascot "thinking" shimmer, used while the agent plans a session,
< 2s) · audio-unavailable fallback (if TTS fails: the picture + first-letter hint appears
instead, plus a small "sound isn't working" note for the parent) · empty states
(Collection with zero creatures — "your first friend is almost here!"; parent dashboard
with no sessions yet). Also: hover AND keyboard-focus styles for every interactive
element (she may use either), and disabled states for the primary button until an answer
is entered.

---

## 9. STYLING-CONTEXT MANIFEST (output rules for the design tool — required)

Per `docs/sops/mockup-implementation.md`, the handoff must be implementation-ready:

1. **Target stack:** Flask/Jinja-served **vanilla HTML + CSS custom-property design
   tokens + plain scoped CSS + vanilla JS**. NO React, NO Tailwind, NO CSS-in-JS,
   NO utility classes, NO build step (locked by ADR-003).
2. **Token vocabulary:** emit ALL values as semantic tokens prefixed `--sq-*`
   (`--sq-color-bg`, `--sq-color-ink`, `--sq-color-primary`, `--sq-color-success`,
   `--sq-color-almost`, `--sq-color-star`, `--sq-space-1..8`, `--sq-radius-card`,
   `--sq-radius-tile`, `--sq-font-display`, `--sq-text-word`, `--sq-shadow-card`…).
   One `tokens.css`. **No raw hex/px inside components.**
3. **Component library:** define reusable primitives and use them everywhere —
   `Button` (primary/quiet/icon), `TaskCard`, `LetterBox`, `LetterTile`, `SoundBoxRow`,
   `AudioButton`, `ProgressDots`, `StarMeter`, `Mascot`, `Chest`, `Bucket`, `WordChip`,
   `TeachCard`, `RadarChart` (parent). Same component = same pixels on every screen.
4. **Output rules:** semantic HTML + scoped classes (`.sq-*`) referencing `var(--sq-*)`;
   zero inline styles; flag any value that isn't in the token palette instead of
   silently inventing it.
5. **Scope:** ALL screens/states in §4–§8 as one coherent IA — not a single hero frame.
   Kid screens at a 1280×800 desktop viewport (primary) + note anything that must adapt
   at tablet width.
6. **Handoff format:** the structured "Send to Claude Code" bundle (component tree +
   tokens + layout hierarchy + assets), not just images. Include the mascot + creatures
   as SVG assets.
7. **Fonts:** Lexend (Google Fonts, will be self-hosted). Specify exact weights used.

---

## 10. What NOT to design
Login/auth (none exists) · onboarding wizards · social/sharing · ads/upsells · dark mode
(v1 is the single warm theme) · mobile-phone layouts (desktop/tablet only for v1) ·
any leaderboard against other people (she competes only with herself, by design).
