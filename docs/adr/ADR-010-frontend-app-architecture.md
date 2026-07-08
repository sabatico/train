# ADR-010 — Frontend app architecture (SPA shell, registry, router, audio wrapper)

**Status:** Accepted *(2026-07-07; frozen at token-lock / start of B7)*
**Date:** 2026-07-07 · **Related:** ADR-003 (stack), ADR-004 (WebView-clean seam), ADR-005 (item contract), `DESIGN_BRIEF.md`, the design handoff

## Context
ADR-003 locked *how we style* (tokens + scoped CSS, vanilla JS, no build). It did not decide *how the app is shaped*: one page or many? where does the exercise-rendering registry live? how do screens transition with the animations the design calls for (card slide-in, stars flying to the dot row, correction overlay)? how is TTS structured so the Stage-2 native-bridge swap (ADR-004 seam 4) touches one file? This decides the frontend's skeleton before B7 builds on it.

## Decision

**A single-page shell for the kid app** (`/app`), server-rendered once by Jinja, with client-side view switching — NOT multi-page navigation. Rationale: the session is one continuous animated flow (DESIGN_BRIEF §4/§5); full page loads would kill the transitions and re-fetch on every item. The parent app (`/parent/*`) stays plain multi-page (no animation needs).

**Modules (vanilla ES modules, no bundler — served as static files):**
- `app.js` — boot: fetch session state, own the view lifecycle.
- `router.js` — a tiny view switcher (home → session → reward → collection); pushes to `history` so back works, but no framework router.
- `registry.js` — **the component registry**: `type → render(item, mount, onAnswer)`. One renderer module per exercise type (`exercises/letter_boxes.js`, …), each consuming the ADR-005 payload and returning DOM built from `.sq-*` components. Adding exercise type #11 = one file + one registry line.
- `components/` — the shared primitives from the handoff (`Button`, `TaskCard`, `LetterBox`, `LetterTile`, `AudioButton`, `ProgressDots`, `StarMeter`, `Mascot`, `Chest`, `Bucket`, …) as factory functions returning elements; **built strictly from `components.css` classes, zero inline styles** (ADR-003 lint).
- `speech.js` — **the sole TTS wrapper** over `speechSynthesis`: `speak(word, {rate})`, unlimited replay, autoplay-gesture handling (iOS/Safari requires a user gesture; first tap unlocks), and the failure fallback (DESIGN_BRIEF §8: on no-voice, surface picture + first-letter hint + a small parent note). **Nothing else in the frontend calls `speechSynthesis` directly** — this is the ADR-004 seam where a native WebView TTS/audio bridge drops in.
- `api.js` — the only `fetch` layer to `/api/*` (server-authoritative; the client never grades).

**State:** the server owns session/correctness state (ADR-009); the client holds only ephemeral view state. No client state library.

**Correction overlay is ONE reusable component** (`components/correction.js`) driven by the ADR-005 `reveal` payload — implements the DESIGN_BRIEF §5 beats identically for every exercise (attempt dissolves → reveal with markers → retype → star). This is the most-reused, most-invariant-bound UI piece; it exists once.

**Assets:** Lexend self-hosted in `static/fonts/` (no external request during a child's session, per third-party-services); mascot/creature SVGs from the handoff lifted into `static/img/`.

## Alternatives rejected
- **Multi-page Jinja (a route per screen)** — simplest with Flask, but every item transition is a full reload — no card slide, no stars-fly animation, a flash between items; wrong for a flow-based, animation-heavy kid experience.
- **A framework SPA (React/Vue/Svelte/HTMX)** — re-litigates ADR-003; adds a build step and dependency drift for interactions a ~300-line registry handles.
- **TTS called ad-hoc wherever needed** — scatters the Web Speech quirks (autoplay unlock, voice selection, failure) across every exercise and makes the Stage-2 native-audio swap a hunt-and-replace. One wrapper is the seam.

## Consequences
- **Makes easy:** the designed animations/flow; adding exercise types (one registry entry); the WebView native-bridge swap (one file: `speech.js`, plus `api.js` base URL); pixel-perfect implementation from the handoff (components map 1:1 to `.sq-*`).
- **Makes hard / costs:** manual DOM/state management (mitigated: server owns real state, views are dumb re-renders); hand-rolled drag for `word_builder`/`word_sort` (one small helper).
- **Follow-ups:** the token-lock pass adopts `tokens.css`/`components.css` into `static/css/`; a no-`speechSynthesis`-outside-`speech.js` lint; the registry contract frozen with ADR-005.
- **Risks accepted:** if the kid app ever grows far past the planned screens, manual state could strain — accepted (ADR-003's deliberately-small-product bet).
