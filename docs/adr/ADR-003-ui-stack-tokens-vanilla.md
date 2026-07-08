# ADR-003 — UI stack: CSS-custom-property tokens + scoped CSS + vanilla-JS component registry (no framework)

**Status:** Accepted
**Date:** 2026-07-07 · **Related:** `docs/sops/ui-development-guardrails.md`, `docs/sops/mockup-implementation.md`, `DESIGN_BRIEF.md`, ADR-002 (the shared exercise contract)

## Context
The UI is a small set of radically simple screens (per ADHD/dyslexia design rules in `PLAN.md` §6) whose central mechanism is: the backend/agent emits `{type, payload}` and the frontend renders the matching exercise component. The UI guardrails SOP requires one locked styling stack, chosen for agent-reliability over novelty. Claude Design mockups will be implemented pixel-perfect per the mockup SOP, which needs a token layer to map extracted values onto.

## Decision
- **Tokens:** one `static/css/tokens.css` holding every brand value as `--sq-*` custom properties (color, type scale, spacing, radius, shadow, motion). No component uses a raw value.
- **Styles:** plain scoped CSS, one file per component (`static/css/components/*.css`), class convention `.sq-<component>`. **Zero inline styles** (lint-enforced per the SOP).
- **Behavior:** vanilla ES modules; a **component registry** maps exercise `type` → renderer function; screens compose primitives (Button, Card, LetterBox, StarMeter…). Jinja templates only for the page shells.
- **No build step, no framework, no CSS framework.**

## Alternatives rejected
- **React/Vue/Svelte** — the interactivity here (render card, collect input, animate stars) doesn't need a virtual DOM or a toolchain; a build step adds the single biggest source of agent/env friction for zero product gain at this size.
- **Tailwind** — utility classes scatter the design system into markup; the mockup-implementation SOP works best with semantic tokens + component classes; also adds a build step.
- **HTMX / server-rendered swaps** — attractive with Flask, but the exercise interactions (per-letter inputs, drag tiles, timed game) are inherently client-side; splitting logic across both sides would be messier than one JS registry.

## Consequences
- **Makes easy:** pixel-perfect implementation from Claude Design (extract → tokens); cheap-model builders can't dependency-drift; instant reload during development; the same `{type,payload}` contract serves frontend and agent tool schemas.
- **Makes hard / costs:** no framework conveniences (state management is manual — keep screens dumb, state on the server); drag-and-drop needs a small hand-rolled or single-file helper.
- **Follow-ups:** token-lock pass (runner B2) once mockups arrive; no-inline-styles lint in the gates (T-008).
- **Risks accepted:** if the UI ever grows far beyond the planned screens, a framework migration would be real work — accepted; the product is deliberately small.
