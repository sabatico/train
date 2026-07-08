// The correction overlay — the most important interaction (DESIGN_BRIEF §5).
// A wrong answer never lingers: "Almost!" → the correct word large with the
// tricky part highlighted + a kid-voice why (from the agent or canned) → she
// retypes it right → continue. One reusable component for every exercise.

import { el } from "./dom.js";
import * as speech from "./speech.js";

function wordWithMarkers(word, markers) {
  const hot = new Set();
  for (const group of markers || []) for (const idx of group) hot.add(idx);
  const node = el("div", { class: "sq-word sq-word--xl" });
  [...word].forEach((ch, i) => {
    node.appendChild(el("span", { class: hot.has(i) ? "sq-word__hot" : "", text: ch }));
  });
  return node;
}

// reveal = { target, markers, why, audio }; submitRetype(attempt) -> Promise(result)
export function showCorrection(root, reveal, submitRetype, onContinue) {
  const scrim = el("div", { class: "sq-overlay-scrim" });

  const input = el("input", {
    class: "sq-input-word",
    attrs: { type: "text", autocomplete: "off", "aria-label": "type it correctly" },
  });
  const go = el("button", {
    class: "sq-btn sq-btn--star",
    text: "Got it!",
    attrs: { type: "button", disabled: "" },
    on: { click: submit },
  });
  input.addEventListener("input", () => { go.disabled = !input.value.trim(); });
  input.addEventListener("keydown", (e) => { if (e.key === "Enter" && !go.disabled) submit(); });

  let submitting = false;
  async function submit() {
    if (submitting) return; // guard against a double-tap re-entering
    submitting = true;
    go.disabled = true;
    await submitRetype(input.value);
    if (scrim.parentNode) root.removeChild(scrim);
    onContinue();
  }

  const card = el("div", { class: "sq-card sq-card--almost" }, [
    el("p", { class: "sq-card__instruction", text: "Almost! Let's look together 💛" }),
    wordWithMarkers(reveal.target, reveal.markers),
    el("div", { class: "sq-row" }, [
      el("button", {
        class: "sq-audio",
        text: "🔊",
        attrs: { type: "button", "aria-label": "hear the word" },
        on: { click: () => speech.speak(reveal.audio) },
      }),
      el("p", { class: "sq-explain", text: reveal.why }),
    ]),
    el("p", { class: "sq-card__instruction", text: "Now you type it 🙂" }),
    input,
    go,
  ]);

  scrim.appendChild(card);
  root.appendChild(scrim);
  speech.speak(reveal.audio);
  setTimeout(() => input.focus(), 50);
}
