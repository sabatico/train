# ADR-013 — OpenAI TTS as the pre-generated dictation-audio provider

**Status:** Accepted *(owner chose the provider + approach 2026-07-08; audio generation gated on the owner's OpenAI key — TBD-008)*
**Date:** 2026-07-08 · **Related:** ADR-002 (DeepSeek LLM), ADR-004/010 (`speech.js` seam), `PLAN.md` §5, T-014

## Context
The browser `speechSynthesis` voice is robotic and unattractive for a young child (owner feedback 2026-07-08). The word banks are a fixed, curated, finite list (736 words), so audio can be generated ONCE rather than synthesized live. `speech.js` was already built as the single TTS wrapper (ADR-004 seam) precisely to allow this swap. DeepSeek (our LLM, ADR-002) has no TTS, so nicer audio requires a second provider.

## Decision
Use **OpenAI TTS** (`tts-1`, a warm voice such as `nova`) to **pre-generate** one MP3 per word-bank word into `static/audio/<word>.mp3` (build-time script `scripts/generate_audio.py`, idempotent/resumable). The frontend `speech.js` **prefers the cached clip and falls back to browser TTS** for any missing word — so the change is purely additive and the app keeps working before/without audio. `OPENAI_API_KEY` is a second secret (TTS only). Generation is a build step, never a runtime call — zero per-play cost, latency, or network dependence for the child (critical for an ADHD learner) and it works offline.

## Alternatives rejected
- **ElevenLabs** — the most natural/expressive voices, but pricier and a heavier account; OpenAI TTS is natural enough at a fraction of the cost/effort. Fallback: `generate_audio.py` isolates the provider, so switching is a one-script change.
- **Realtime neural TTS (per play)** — flexible for arbitrary text (useful once free-writing exists), but adds per-play cost, latency, and a network dependency to every audio tap. Pre-generation wins for a fixed word list; revisit realtime when `sentence_scribe` needs to speak arbitrary text.
- **Keep browser TTS** — free and zero-setup, but it's the robotic voice we're replacing. It remains the graceful fallback.
- **Bundle audio in git vs regenerate** — deferred; clips are small and regenerable, decide when first generated.

## Consequences
- **Makes easy:** natural voice, instant playback, offline, ~free per play; provider swap (one script); the frontend already consumes it via `speech.js`.
- **Makes hard / costs:** a one-time generation pass + a second API key + ~10–20 MB of MP3s to store; regenerate when the banks grow (the script only makes missing clips, so it's cheap).
- **Follow-ups:** owner provides `OPENAI_API_KEY` (TBD-008) → run `scripts/generate_audio.py`; decide whether to commit the MP3s.
- **Risks accepted:** dependence on a second vendor for the *nice* audio — bounded by the browser-TTS fallback (the app never loses audio entirely).
