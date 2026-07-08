// Exercise renderers — one per type (ADR-005/010). Each returns a DOM node and
// calls onSubmit(attempt) when the child completes the item. Built only from
// .sq-* components. The registry maps item.type → renderer.

import { el } from "./dom.js";
import * as speech from "./speech.js";

function audioButton(word, { hero = false } = {}) {
  return el("button", {
    class: hero ? "sq-audio sq-audio--hero" : "sq-audio",
    text: "🔊",
    attrs: { type: "button", "aria-label": "hear the word" },
    on: { click: () => { speech.unlock(); speech.speak(word); } },
  });
}

function instruction(text) {
  return el("p", { class: "sq-card__instruction", text });
}

function doneButton(label, onClick) {
  const btn = el("button", {
    class: "sq-btn sq-btn--primary",
    text: label,
    attrs: { type: "button", disabled: "" },
    on: { click: onClick },
  });
  return btn;
}

function shuffle(arr) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// ---- word_builder: tap tiles into sound boxes ----
function renderWordBuilder(item, onSubmit) {
  const word = item.prompt.audio_word;
  const boxes = item.payload.sound_boxes.map(() => null); // filled with tile text
  const boxEls = [];
  const boxRow = el("div", { class: "sq-soundbox-row" });
  item.payload.sound_boxes.forEach((b, i) => {
    const box = el("div", {
      class: "sq-soundbox" + (b.width === "digraph" ? " sq-soundbox--digraph" : ""),
      on: { click: () => returnTile(i) },
    });
    boxEls.push(box);
    boxRow.appendChild(box);
  });

  const tray = el("div", { class: "sq-tile-tray" });
  const done = doneButton("Done", () => onSubmit(boxes.join("")));

  function refresh() {
    boxEls.forEach((box, i) => {
      box.textContent = boxes[i] || "";
      box.classList.toggle("sq-soundbox--filled", !!boxes[i]);
    });
    done.disabled = boxes.some((b) => b === null);
  }
  function placeTile(text, tileEl) {
    const next = boxes.indexOf(null);
    if (next === -1) return;
    boxes[next] = text;
    tileEl.classList.add("sq-tile--used");
    tileEl.disabled = true;
    refresh();
  }
  function returnTile(i) {
    if (!boxes[i]) return;
    const text = boxes[i];
    boxes[i] = null;
    const t = tileEls.find((te) => te.dataset.text === text && te.disabled);
    if (t) { t.classList.remove("sq-tile--used"); t.disabled = false; }
    refresh();
  }

  const tileEls = shuffle(item.payload.tiles).map((text) => {
    const tile = el("button", {
      class: "sq-tile" + (text.length > 1 ? " sq-tile--digraph" : ""),
      text,
      attrs: { type: "button" },
    });
    tile.dataset.text = text;
    tile.addEventListener("click", () => placeTile(text, tile));
    tray.appendChild(tile);
    return tile;
  });

  refresh();
  return el("div", { class: "sq-stack" }, [
    el("div", { class: "sq-emoji-prompt", text: item.prompt.image_emoji || "🔤" }),
    audioButton(word),
    instruction("Build the word"),
    boxRow,
    tray,
    done,
  ]);
}

// ---- letter_boxes: one input per letter ----
function renderLetterBoxes(item, onSubmit) {
  const word = item.prompt.audio_word;
  const n = item.payload.boxes.length;
  const inputs = [];
  const row = el("div", { class: "sq-letterbox-row" });
  for (let i = 0; i < n; i++) {
    const inp = el("input", {
      class: "sq-letterbox",
      attrs: { type: "text", maxlength: "1", inputmode: "text", "aria-label": `letter ${i + 1}` },
    });
    inp.addEventListener("input", () => {
      inp.value = inp.value.slice(-1);
      if (inp.value && i < n - 1) inputs[i + 1].focus();
      refresh();
    });
    inp.addEventListener("keydown", (e) => {
      if (e.key === "Backspace" && !inp.value && i > 0) inputs[i - 1].focus();
      if (e.key === "Enter" && !done.disabled) onSubmit(collect());
    });
    inputs.push(inp);
    row.appendChild(inp);
  }
  const collect = () => inputs.map((x) => x.value).join("");
  const done = doneButton("Done", () => onSubmit(collect()));
  function refresh() { done.disabled = inputs.some((x) => !x.value); }

  const node = el("div", { class: "sq-stack" }, [
    el("div", { class: "sq-emoji-prompt", text: item.prompt.image_emoji || "🔤" }),
    audioButton(word),
    instruction("Type the word"),
    row,
    done,
  ]);
  node.focusFirst = () => inputs[0] && inputs[0].focus();
  return node;
}

// ---- echo_dictation: hear it, type it (no picture reveal) ----
function renderEchoDictation(item, onSubmit) {
  const word = item.prompt.audio_word;
  const input = el("input", {
    class: "sq-input-word",
    attrs: { type: "text", autocomplete: "off", "aria-label": "type what you hear" },
  });
  const done = doneButton("Done", () => onSubmit(input.value));
  input.addEventListener("input", () => { done.disabled = !input.value.trim(); });
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !done.disabled) onSubmit(input.value);
  });
  // auto-speak once on show
  setTimeout(() => speech.speak(word), 350);
  const node = el("div", { class: "sq-stack" }, [
    audioButton(word, { hero: true }),
    instruction("Listen, then spell it"),
    input,
    done,
  ]);
  node.focusFirst = () => input.focus();
  return node;
}

const RENDERERS = {
  word_builder: renderWordBuilder,
  letter_boxes: renderLetterBoxes,
  echo_dictation: renderEchoDictation,
};

export function renderExercise(item, onSubmit) {
  const renderer = RENDERERS[item.type] || renderEchoDictation;
  return renderer(item, onSubmit);
}
