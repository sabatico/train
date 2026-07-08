"""The AI teacher-agent (DeepSeek) — session planning, kid-voice corrections, and
the teacher notebook (ADR-002/012). Every call has a deterministic engine fallback;
the app never stalls on the API, and no child PII is ever sent (invariant #2).
"""
