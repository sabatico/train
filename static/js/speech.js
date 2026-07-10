// The SOLE TTS wrapper (ADR-004/010 seam). Nothing else calls speechSynthesis
// directly — a native WebView TTS bridge (Stage 2) replaces just this file.
// Unlimited replay, rate-adjustable, gesture-unlocked for iOS/Safari, and a
// graceful "no voice" fallback signal for the UI (DESIGN_BRIEF §8).

let unlocked = false;

export function available() {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

// iOS/Safari require a user gesture before the first utterance. Call once from a
// tap handler to prime it.
export function unlock() {
  if (unlocked || !available()) return;
  try {
    const u = new SpeechSynthesisUtterance("");
    window.speechSynthesis.speak(u);
    unlocked = true;
  } catch {
    /* ignore — will simply fall back if speech never works */
  }
}

function browserSpeak(word, rate) {
  if (!available() || !word) return false;
  try {
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(String(word));
    u.rate = rate;
    window.speechSynthesis.speak(u);
    return true;
  } catch {
    return false;
  }
}

// Shared "currently playing" handle + a read-aloud busy guard.
let _current = null;
let _reading = false;

function stopCurrent() {
  if (_current) {
    try {
      _current.pause();
      _current.currentTime = 0;
    } catch {
      /* ignore */
    }
    _current = null;
  }
  if (available()) {
    try {
      window.speechSynthesis.cancel();
    } catch {
      /* ignore */
    }
  }
}

// Read arbitrary on-screen text aloud in the kid voice via /api/tts (cached
// server-side), falling back to browser TTS if the endpoint is unavailable.
// ANTI-SPAM: while a read is already in flight, extra taps are ignored — so
// spamming the button never fires parallel API calls or overlapping audio.
export async function speakText(text, { rate = 0.95 } = {}) {
  if (!text || _reading) return;
  _reading = true;
  stopCurrent();
  // safety net: whatever goes wrong, the guard NEVER sticks (a hung fetch once
  // made every later tap dead-silent — owner-found bug)
  const failsafe = setTimeout(() => { _reading = false; }, 15000);
  const done = () => {
    clearTimeout(failsafe);
    _reading = false;
  };
  const fallback = () => browserSpeakUntil(text, rate, done);
  try {
    const ctrl = new AbortController();
    const abortTimer = setTimeout(() => ctrl.abort(), 8000); // never hang on TTS
    const res = await fetch("/api/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
      signal: ctrl.signal,
    });
    clearTimeout(abortTimer);
    if (res.ok) {
      const url = URL.createObjectURL(await res.blob());
      const audio = new Audio(url);
      _current = audio;
      const cleanup = () => {
        URL.revokeObjectURL(url);
        if (_current === audio) _current = null;
      };
      audio.addEventListener("ended", () => { cleanup(); done(); }, { once: true });
      audio.addEventListener("error", () => { cleanup(); fallback(); }, { once: true });
      try {
        await audio.play();
      } catch {
        cleanup();
        fallback();
      }
      return;
    }
  } catch {
    /* timeout or network — fall through to browser TTS */
  }
  fallback();
}

export function isReading() {
  return _reading;
}

// browser-TTS fallback that clears the read-aloud guard when the utterance ends.
function browserSpeakUntil(text, rate, done) {
  if (!available()) {
    done();
    return;
  }
  try {
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(String(text));
    u.rate = rate;
    u.onend = done;
    u.onerror = done;
    window.speechSynthesis.speak(u);
  } catch {
    done();
  }
}

// Prefer a PRE-GENERATED natural-voice clip (T-014, OpenAI TTS), fall back to
// browser TTS when the clip is missing. This is the swap seam (ADR-004): until
// audio files exist under /static/audio/, every word gracefully uses browser TTS.
export function speak(word, { rate = 0.9 } = {}) {
  if (!word) return false;
  stopCurrent(); // never overlap a previous word / read-aloud
  const url = `/static/audio/${encodeURIComponent(String(word).toLowerCase())}.mp3`;
  let fellBack = false;
  const fallback = () => {
    if (!fellBack) {
      fellBack = true;
      browserSpeak(word, rate);
    }
  };
  try {
    const audio = new Audio(url);
    _current = audio;
    audio.addEventListener("error", fallback, { once: true });
    audio.addEventListener("ended", () => { if (_current === audio) _current = null; }, { once: true });
    audio.play().catch(fallback);
    return true;
  } catch {
    return browserSpeak(word, rate);
  }
}
