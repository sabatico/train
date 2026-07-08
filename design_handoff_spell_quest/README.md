# Handoff: Spell Quest — kid UI (core loop + all exercise cards)

## Overview
Spell Quest is a spelling-practice web app for one 7-year-old with dyslexia, dysgraphia and ADHD (10–15 min daily, desktop browser). This bundle covers the **kid-facing screens**: the daily loop (Home → Teach → exercises → correction → Reward → Collection) and all 10 exercise card types, in the committed "pink + yellow sunny" visual direction with a red-panda mascot. Parent screens (P1/P2) and the §8 state set are NOT yet designed — see "Not in this bundle".

The authoritative product spec is `DESIGN_BRIEF.md` (included). Its §2 accessibility invariants and §5 correction flow are **non-negotiable product rules** — implement them exactly.

## About the Design Files
The `.dc.html` files in `design_reference/` are **design references created in an HTML design tool** — they show intended look and behavior but are NOT production code. They use inline styles internally (a constraint of the design tool). **Do not copy their markup.** The task is to recreate these designs in the target stack using the centralized CSS in `css/`.

## Target stack (locked by ADR-003)
Flask/Jinja-served **vanilla HTML + CSS custom-property tokens + plain scoped CSS + vanilla JS**. No React, no Tailwind, no CSS-in-JS, no utility classes, no build step.

- `css/tokens.css` — single source of truth for every value (`--sq-*`). **No raw hex/px in component CSS or markup.**
- `css/components.css` — the `.sq-*` component library. Same component = same pixels everywhere. **Zero inline styles in production markup.** If a design value isn't in the token palette, flag it — don't invent silently.

## Fidelity
**High-fidelity.** Colors, type scale, spacing, radii, shadows and copy in the references are final (values codified in tokens.css). Recreate pixel-perfectly at the primary 1280×800 desktop viewport. The mascot/creature SVGs in the reference files are final flat-geometric art — lift them as-is into `static/` assets.

## Screens (all in `design_reference/Spell Quest.dc.html`, labeled groups 1–3)

### Group 1 — the daily loop
- **S1 Home**: cream page (`--sq-color-bg`), soft `--sq-color-bg-halo` arch behind bobbing mascot; greeting 42px ("Hi Katie!"); streak chip (`.sq-chip--star`, tilted −2°) + mission chip (`.sq-chip--pink`, +1.5°); one hero button `.sq-btn--primary.sq-btn--hero` ("Start!"); two `.sq-btn--quiet` chips (My Collection / Games); level badge `.sq-chip--badge` top-right. No nav, no settings — parent routes are separate URLs.
- **S3 Teach card**: `.sq-card--teach` (yellow); pattern title 52px + emoji; ONE rule sentence 30px; example pair hop→hope with pattern letters in `.sq-word__hot`; `.sq-audio--star` reads card; `.sq-btn--star` "Got it!".
- **S2 session shell**: top `.sq-dots` row is the ONLY chrome (done = ⭐ tilted alternately, current = pulsing pink dot, upcoming = hollow); quiet ⏸ `.sq-btn--ghost` top-right ("Stop for today?" prompt); mascot small bottom-left (`.sq-mascot`); centered `.sq-card`; Done button bottom-right of card, disabled until an answer exists.
- **§5 Correction overlay** (ONE reusable component, most important interaction): scrim `.sq-overlay-scrim`; `.sq-card--almost` (amber — NEVER red, never ✗); beats: (1) "Almost!" ~1s, child's attempt dissolves and is never shown again → (2) correct word 76px with `.sq-word__hot` letters (+🛡️/❤️ markers), `.sq-explain` strip with auto-read TTS line → (3) empty retype input identical to the exercise's → (4) gentle ✅ + 1 star, close.
- **S4 Reward**: chest SVG, 3 stars arcing out, "+9 stars today!", `.sq-meter` toward next level, hatching tease chip, one `.sq-btn--primary` "Yay! Done". Confetti (`.sq-confetti`) allowed here only.
- **S5 Collection**: `.sq-shelf` rows; mastered = pastel creature SVG + `.sq-creature__label` (pattern name); unmastered = `.sq-egg` with "?"; ⭐ total + level badge at top; back arrow.

### Group 2 — writing beyond one word
- **E7 echo dictation**: quietest card; `.sq-audio--hero` 120px (auto-plays once), faint hint picture (opacity .28), ONE wide free input, Done.
- **E8 phrase dictation**: one input **per word**, widths proportional to word length, laid out as one sentence line; `.sq-audio--word` ghost replay under each; completed word gets `--sq-color-success` border.
- **E9 sentence scribe**: prompt picture + 🔊; `.sq-lines` ruled area (3 lines max, 36px text on 76px rules). Review card: praise line FIRST (`--sq-color-success-ink`), her sentence rendered **corrected** (raw errors never displayed), ≤2 `.sq-sentence-highlight` words, then per-word retype (letter boxes) — "1 of 2" progress note.

### Group 3 — other exercises
- **E1 word builder**: `.sq-soundbox-row` (one box per phoneme, `--digraph` boxes wider) + `.sq-tile-tray` of `.sq-tile`s (needed letters + 2–3 distractors, alternating ±2° tilt, `--digraph` wide "sh" tile, `--used` state). Tile taps hop (300ms ease-out) into next empty box; no live error nagging before Done.
- **E2 letter boxes** (workhorse): `.sq-letterbox` per letter (72×80, 44px letters), phoneme brackets under the row (SVG: yellow arc joins digraph letters, flat dashes per single); typing auto-advances; Enter = Done.
- **E3 missing letters**: static letters 64px + `.sq-letterbox` gaps only; focus jumps between gaps.
- **E5 word sort**: center `.sq-wordchip`; two `.sq-bucket`s with icon + label + 2 tiny example words; correct = chip settles + chime; wrong = chip drifts back, correct bucket `.sq-bucket--hint` glows.
- **E6 heart word**: `.sq-beats` pills (LOOK/COVER/WRITE/CHECK); word 84px with ❤️ above tricky letters; "Cover it!" `.sq-btn--star` slides a flap over the word; WRITE = letter boxes from memory; CHECK = flap lifts, side-by-side.
- **E4 b/d ninja**: mnemonic intro first; game = `.sq-bubble`s floating (pink targets, blue foils), correct tap pops +✨, wrong tap `.sq-bubble--wobble` only; progress = `.sq-meter` filling, NEVER a countdown clock.
- **E10 beat yesterday**: pre-screen with record big ("7 words ⭐ — beat it?"), Go, meter-only time cue; end warm win/no-win copy, zero shame.

## Interactions & Behavior
- Motion: 200–400ms, `--sq-ease` ease-out. 3D buttons press down 2px on hover/press. Respect `prefers-reduced-motion` (rule included in components.css).
- Audio: every dictated item has an unlimited-replay 🔊 identical on every press. TTS failure fallback: show picture + first-letter hint + small parent note ("sound isn't working").
- Primary Done buttons disabled (`:disabled` style) until an answer is entered.
- Hover AND `:focus-visible` styles required on every interactive element (trackpad + keyboard).
- All hit targets ≥ `--sq-size-touch` (56px).
- Kid text: Lexend 400/500/600 only, lowercase-first, letter-spacing 0.05em on words, line-height ≥1.6, never italic/ALL-CAPS/justified, never text over images/gradients.
- NEVER: red, ✗, "wrong", visible misspellings (outside the ~1s dissolve), visible timers/clocks, decreasing scores, sad mascot.

## State Management (vanilla JS)
- Session: item list (8–12), current index, per-item answer state, stars earned (2 first-try / 1 corrected), correction-overlay state machine (beats 1–4).
- Home: streak count, today's mission, level + star totals.
- Games: filled-meter progress, word/pop counter (counts UP), personal record.
- Persistence & content come from the Flask backend (per-item TTS text, explanation lines, patterns).

## Design Tokens
See `css/tokens.css` — colors, 4px-base spacing scale (`--sq-space-1..8`), type scale, radii (card 28 / tile 18 / pill), offset "storybook" shadows, focus rings, motion durations, component sizes (letter box 72×80, digraph sound box 128px wide, audio button 88/120px). Fonts: **Lexend 400/500/600**, self-hosted (currently Google Fonts in the references); fallback OpenDyslexic.

## Assets
- Red-panda mascot + 3 creatures + eggs + chest + shelf: inline SVGs in the reference files — extract to `static/img/*.svg`. Mascot has expression variants (happy default, encouraging lean-in for correction, proud for review) — differ only in eye/mouth paths.
- Emoji used as iconography by design (🔊 ⭐ 🔥 🪄 🥚 ❤️ 🛡️ etc.).

## Files
- `design_reference/Spell Quest.dc.html` — committed design, all screens (groups 1–3)
- `design_reference/Spell Quest Directions.dc.html` — exploration history (turn 1 directions, turn 2 first pass)
- `css/tokens.css`, `css/components.css` — the centralized CSS to build on
- `DESIGN_BRIEF.md` — full product spec

## Not in this bundle (designed next)
§8 states (loading shimmer, audio-fallback, empty states, S4b level-up, S4c hatch), parent dashboard P1 (radar chart, error log — misspellings allowed there only) and settings P2, "grown-ups only" hold-to-enter gate.
