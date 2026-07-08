# Third-Party Services — Spell Quest

> **The single inventory of every external service the project depends on — what it is, WHY we use it, and how it's wired** (accounts, endpoints, config by NAME — **never secret values**). Built so a human or agent can see the whole external-dependency surface at a glance before touching any integration. **Keep current when an account/endpoint/config/DNS record changes.**
> **⚠️ Secrets:** this file lists secrets **by name and location only** (which env var, which secret store) — never the value.

## Services
| Service | What it does for us | WHY this one (vs alternatives) | Status | Plan / cost | Owner-action needed |
|---------|---------------------|--------------------------------|--------|-------------|---------------------|
| DeepSeek API | The teacher-agent LLM: session planning, kid-voice error explanations, sentence review, weekly parent notes, `memory.md` notebook | Owner's choice (ADR-002) — owner provides the account; OpenAI-compatible API keeps the client trivial; very low per-token cost suits daily kid sessions | **key live** (verified 2026-07-07); module not yet built | pay-as-you-go, expected < $2/mo at 1 session/day | none |
| OpenAI TTS (`tts-1`) | Pre-generated natural dictation audio (ADR-013) — one MP3 per word, cached static | Owner chose it (2026-07-08) over ElevenLabs (pricier) / realtime (per-play cost); natural + cheap; `speech.js` seam already isolates it | planned / gated on key | ~one-time pennies for 736 clips | provide `OPENAI_API_KEY`, run `scripts/generate_audio.py` |
| Browser `speechSynthesis` (Web Speech API) | TTS FALLBACK when a pre-generated clip is missing | Built into every browser: free, offline, zero deps; the graceful fallback under ADR-013 | live (browser built-in) | free | none |
| Google Fonts — Lexend | The dyslexia-friendly UI typeface | Lexend is designed for reading proficiency, free, and can be **self-hosted** — we vendor the woff2 into `static/fonts/` so the child's sessions make zero external requests | planned | free (OFL) | none |

## Configuration (per service)
### DeepSeek API
- **Account / project:** owner's personal DeepSeek account (owner-managed).
- **Endpoints / regions:** `https://api.deepseek.com/chat/completions` (OpenAI-compatible); model `deepseek-chat` (function-calling capable — needed for exercise tool schemas). Note: `deepseek-chat` is an alias — probe on 2026-07-07 served `deepseek-v4-flash`; the served model can change under us, so agent output validation (ADR-002 rule 2) is load-bearing.
- **Config (env vars + non-secret dev values):** `DEEPSEEK_MODEL` = `deepseek-chat`; `DEEPSEEK_BASE_URL` = `https://api.deepseek.com`; `SPELLQUEST_AGENT_LIVE` = `0` (default off — set `1` to enable live kid-voice feedback; off keeps dev/tests deterministic and free). TLS uses the `certifi` CA bundle (macOS Python lacks a system trust store).
- **Secrets by NAME:** `DEEPSEEK_API_KEY` → stored in gitignored `.env`. *(value never here)*
- **DNS / domains:** none.
- **Limits / gotchas:** every call must respect **invariant #2 — no child PII in prompts** (words, skill states, error tags only; the child is "the student" in prompts). Timeouts/failures must degrade to the deterministic engine (ADR-002 fallback contract) — a slow API must never stall a 7-year-old mid-session; use tight timeouts (~10s plan / ~5s feedback) and the canned lines as fallback.

### Browser speechSynthesis
- **Config:** voice + rate live in `data/profile.json` (parent settings, PAR-04).
- **Limits / gotchas:** available voices differ per browser/OS; iOS/Safari requires a user gesture before first utterance; always render the 🔊 replay button (invariant-adjacent: replays are unlimited and never penalized).

## Stubbed / not-yet-live integrations
| Service | Marker | Why stubbed | Unblock trigger |
|---------|--------|-------------|-----------------|
| *(none — DeepSeek key landed 2026-07-07 and was probe-verified before any code existed, so no `STUB:DEEPSEEK` marker was ever written; `agent/teacher.py` builds against the live API from the start, mocked only in tests)* | | | |

> Read this **before touching any integration.** New service or changed config ⇒ update this file in the same slice (it's a running file — part of Done).
