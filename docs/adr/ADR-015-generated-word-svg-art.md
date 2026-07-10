# ADR-015 — Word pictures = verified generated SVG art (not emoji)

**Status:** Accepted *(owner idea + "every depictable word" scope, 2026-07-10)*
**Date:** 2026-07-10 · **Related:** ADR-013 (DeepSeek), the emoji audit (act-026); supersedes emoji as the primary picture cue

## Context
Emoji cues were unreliable for a dyslexic child: the vocabulary is limited and often ambiguous (🥛 for "sip", 📋 for "plan"), so the act-026 audit removed 557 of them — leaving most words with no picture. A picture is a genuine support for this learner when it's unmistakable. DeepSeek can author SVG *code*; the lead can *render and visually verify* each result (same bar as the audit's back-translation), so we can produce custom, on-brand, unambiguous art per word.

## Decision
Generate a simple flat SVG icon per **drawable** word (owner scope: every depictable word across the banks — concrete nouns + clearly-depictable actions), gated by a two-stage pipeline (`agent/svg_art.py`, `scripts/gen_word_svgs.py`):
1. **Classify** (DeepSeek): drawable? + a one-line drawing brief. Abstract/relational/function words (the, was, plan, come, from) → **no image** (correct: no drawing disambiguates them; audio is their cue).
2. **Generate** (DeepSeek): flat, single-object, palette-friendly SVG, **no text/letters** (a spelling picture must never leak the spelling), sanitized for safe static serving (no script/foreignObject/external refs).
3. **Verify** (lead, visual): render galleries, keep only art a child would name as exactly that word; regenerate once with a stronger brief, else drop to imageless. Manifest `data/word_images.json` records status.
4. **Serve fresh**: a word bank entry gains `"image": "words/<w>.svg"` when verified; `contracts.build_item` puts it on `prompt.image`; renderers prefer **SVG → emoji → neutral 🔤**. Because items are rebuilt from the current bank at serve time (session freshness fix), new/replaced art reaches in-flight sessions instantly. Never shown on `echo_dictation` (pure recall).

## Alternatives rejected
- **Emoji only** — ambiguous + sparse (the problem we're fixing).
- **A real image model (DALL·E/SD)** — photoreal/raster is heavier, off-brand, and no cheaper to verify; flat SVG matches the design system and is tiny + crisp at any size. Revisit only if SVG quality caps out.
- **Ship LLM SVGs unverified** — the pilot was ~10/12 good; the ~15% failures (a "ship" blob, a "bed" that read as a stall) would teach the wrong word. The visual gate is non-negotiable — same principle as the emoji back-translation.
- **Draw abstract words too** — impossible to disambiguate; imageless + audio is the right answer.

## Consequences
- **Makes easy:** unambiguous, on-brand, scalable pictures for far more words than emoji covered; tiny committed assets; instant propagation via the freshness path.
- **Makes hard / costs:** the lead's visual verification is the throughput bottleneck (batched gallery review); generation cost (small, DeepSeek); a manifest to maintain.
- **Follow-ups:** periodic re-verify as a drift guard; `beat_yesterday` (T-013) and other backlog unaffected.
