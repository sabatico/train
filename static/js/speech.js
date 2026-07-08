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

export function speak(word, { rate = 0.9 } = {}) {
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
