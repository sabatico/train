// Exercise renderers — one per type (ADR-005/010). Each returns a DOM node and
// calls onSubmit(attempt) when the child completes the item. Built only from
// .sq-* components. The registry maps item.type → renderer.

import { el } from "./dom.js";
import * as speech from "./speech.js";

function say(text) {
  // single words have pre-generated clips; multi-word text uses live TTS
  speech.unlock();
  if (String(text).trim().includes(" ")) speech.speakText(text);
  else speech.speak(text);
}

function audioButton(word, { hero = false } = {}) {
  return el("button", {
    class: hero ? "sq-audio sq-audio--hero" : "sq-audio",
    text: "🔊",
    attrs: { type: "button", "aria-label": "hear it" },
    on: { click: () => say(word) },
  });
}

function instruction(text) {
  return el("p", { class: "sq-card__instruction", text });
}

// Picture cue: a verified SVG (ADR-015) → the audited emoji → a neutral
// placeholder. SVG loads as an <img>; if it 404s we drop to the emoji/placeholder.
function pictureFor(prompt) {
  const emoji = prompt.image_emoji || "🔤";
  if (prompt.image) {
    const wrap = el("div", { class: "sq-emoji-prompt sq-pic" });
    const img = el("img", {
      class: "sq-pic__svg",
      attrs: { src: `/static/img/${prompt.image}`, alt: "", "aria-hidden": "true" },
    });
    img.addEventListener("error", () => { wrap.textContent = emoji; }, { once: true });
    wrap.appendChild(img);
    return wrap;
  }
  return el("div", { class: "sq-emoji-prompt", text: emoji });
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
    pictureFor(item.prompt),
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
    pictureFor(item.prompt),
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

// ---- missing_letters: the word with 1–2 gaps to fill ----
function renderMissingLetters(item, onSubmit) {
  const display = item.payload.display; // letters, null at the blanks
  const inputs = {};
  const row = el("div", { class: "sq-letterbox-row" });
  display.forEach((ch, i) => {
    if (ch === null) {
      const inp = el("input", {
        class: "sq-letterbox",
        attrs: { type: "text", maxlength: "1", "aria-label": `missing letter ${i + 1}` },
      });
      inp.addEventListener("input", () => {
        inp.value = inp.value.slice(-1);
        const keys = Object.keys(inputs).map(Number).sort((a, b) => a - b);
        const next = keys.find((k) => k > i && !inputs[k].value);
        if (inp.value && next !== undefined) inputs[next].focus();
        refresh();
      });
      inp.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !done.disabled) onSubmit(collect());
      });
      inputs[i] = inp;
      row.appendChild(inp);
    } else {
      row.appendChild(el("div", { class: "sq-letterbox sq-letterbox--static", text: ch }));
    }
  });
  const collect = () => display.map((ch, i) => (ch === null ? inputs[i].value : ch)).join("");
  const done = doneButton("Done", () => onSubmit(collect()));
  function refresh() { done.disabled = Object.values(inputs).some((x) => !x.value); }
  refresh();
  const node = el("div", { class: "sq-stack" }, [
    pictureFor(item.prompt),
    audioButton(item.prompt.audio_word),
    instruction("Fill in the missing letters"),
    row,
    done,
  ]);
  node.focusFirst = () => { const k = Object.keys(inputs)[0]; if (k) inputs[k].focus(); };
  return node;
}

// ---- word_sort: which kind of word is it? ----
function renderWordSort(item, onSubmit) {
  const buckets = item.payload.buckets.map((b, i) =>
    el("button", {
      class: `sq-bucket sq-bucket--${i === 0 ? "a" : "b"}`,
      attrs: { type: "button" },
      on: { click: () => onSubmit(b.id) },
    }, [
      el("div", { class: "sq-emoji-prompt", text: b.emoji }),
      el("div", { class: "sq-bucket__label", text: b.label }),
    ])
  );
  return el("div", { class: "sq-stack" }, [
    audioButton(item.prompt.audio_word),
    el("div", { class: "sq-wordchip", text: item.payload.chip }),
    instruction("Which kind of word is it?"),
    el("div", { class: "sq-row" }, buckets),
  ]);
}

// ---- heart_word_spotlight: look → cover → write ----
function renderHeartWordSpotlight(item, onSubmit) {
  const word = item.payload.display_word;
  const tricky = new Set(item.payload.tricky_letters || []);
  const wordEl = el("div", { class: "sq-word sq-word--xl" });
  [...word].forEach((ch, i) => {
    const span = el("span", { text: ch, class: tricky.has(i) ? "sq-word__hot" : "" });
    if (tricky.has(i)) span.appendChild(el("span", { class: "sq-word__heart", text: "❤️" }));
    wordEl.appendChild(span);
  });

  const stack = el("div", { class: "sq-stack" });
  const writeArea = el("div", { class: "sq-stack" });

  const cover = el("button", {
    class: "sq-btn sq-btn--star",
    text: "Cover it! 🙈",
    attrs: { type: "button" },
    on: {
      click: () => {
        wordEl.classList.add("sq-word--covered");
        cover.remove();
        buildWrite();
      },
    },
  });

  function buildWrite() {
    const input = el("input", {
      class: "sq-input-word",
      attrs: { type: "text", autocomplete: "off", "aria-label": "write it from memory" },
    });
    const done = doneButton("Done", () => onSubmit(input.value));
    input.addEventListener("input", () => { done.disabled = !input.value.trim(); });
    input.addEventListener("keydown", (e) => { if (e.key === "Enter" && !done.disabled) onSubmit(input.value); });
    writeArea.appendChild(instruction("Now write it from memory!"));
    writeArea.appendChild(input);
    writeArea.appendChild(done);
    setTimeout(() => input.focus(), 50);
  }

  stack.appendChild(instruction("LOOK at the tricky letters ❤️"));
  stack.appendChild(wordEl);
  stack.appendChild(audioButton(item.prompt.audio_word));
  stack.appendChild(cover);
  stack.appendChild(writeArea);
  say(item.prompt.audio_word);
  return stack;
}

// ---- phrase_dictation: hear the phrase, one input per word ----
function renderPhraseDictation(item, onSubmit) {
  const lengths = item.payload.word_lengths;
  const inputs = lengths.map((len, i) => {
    const inp = el("input", {
      class: "sq-input-word sq-input-word--inline",
      attrs: { type: "text", autocomplete: "off", "aria-label": `word ${i + 1}` },
      cssVars: { "--sq-input-chars": String(Math.max(3, len + 1)) },
    });
    inp.addEventListener("input", refresh);
    inp.addEventListener("keydown", (e) => {
      if (e.key === " " && i < lengths.length - 1) { e.preventDefault(); inputs[i + 1].focus(); }
      if (e.key === "Enter" && !done.disabled) onSubmit(collect());
    });
    return inp;
  });
  const collect = () => inputs.map((x) => x.value.trim()).join(" ");
  const done = doneButton("Done", () => onSubmit(collect()));
  function refresh() { done.disabled = inputs.some((x) => !x.value.trim()); }
  refresh();
  setTimeout(() => say(item.prompt.audio_word), 350);
  const node = el("div", { class: "sq-stack" }, [
    audioButton(item.prompt.audio_word, { hero: true }),
    instruction("Listen, then write each word"),
    el("div", { class: "sq-row" }, inputs),
    done,
  ]);
  node.focusFirst = () => inputs[0].focus();
  return node;
}

// ---- sentence_scribe: hear the sentence, write it ----
function renderSentenceScribe(item, onSubmit) {
  const input = el("input", {
    class: "sq-input-word sq-input-word--wide",
    attrs: { type: "text", autocomplete: "off", "aria-label": "write the sentence" },
  });
  const done = doneButton("Done", () => onSubmit(input.value));
  input.addEventListener("input", () => { done.disabled = !input.value.trim(); });
  input.addEventListener("keydown", (e) => { if (e.key === "Enter" && !done.disabled) onSubmit(input.value); });
  setTimeout(() => say(item.prompt.audio_word), 350);
  const node = el("div", { class: "sq-stack" }, [
    pictureFor(item.prompt),
    audioButton(item.prompt.audio_word, { hero: true }),
    instruction("Listen, then write the sentence"),
    input,
    done,
  ]);
  node.focusFirst = () => input.focus();
  return node;
}

// ---- bd_ninja: pop only the target letter ----
function renderBdNinja(item, onSubmit) {
  const target = item.payload.target_letter;
  const goal = item.payload.goal;
  let hits = 0;
  let wrong = 0;
  const meterFill = el("div", { class: "sq-meter__fill" });
  const grid = el("div", { class: "sq-row sq-bd-grid" });

  function maybeFinish() {
    // dynamic value rides a CSS custom property (the one allowed inline form)
    meterFill.style.setProperty("--sq-meter-pct", `${Math.round((hits / goal) * 100)}%`);
    if (hits >= goal) setTimeout(() => onSubmit(`${hits}/${wrong}`), 400);
  }

  item.payload.letters.forEach((ch) => {
    const bubble = el("button", {
      class: `sq-bubble ${ch === target ? "sq-bubble--target" : "sq-bubble--foil"}`,
      text: ch,
      attrs: { type: "button" },
    });
    bubble.addEventListener("click", () => {
      if (ch === target) {
        hits += 1;
        bubble.disabled = true;
        bubble.classList.add("sq-bubble--popped");
        maybeFinish();
      } else {
        wrong += 1;
        bubble.classList.add("sq-bubble--wobble");
        setTimeout(() => bubble.classList.remove("sq-bubble--wobble"), 400);
      }
    });
    grid.appendChild(bubble);
  });

  return el("div", { class: "sq-stack" }, [
    instruction(`Pop only the “${target}”! ${target === "b" ? "b has its belly in FRONT ⚾" : "d has its bottom BEHIND 🥁"}`),
    el("div", { class: "sq-meter" }, [meterFill]),
    grid,
  ]);
}

const RENDERERS = {
  word_builder: renderWordBuilder,
  letter_boxes: renderLetterBoxes,
  echo_dictation: renderEchoDictation,
  missing_letters: renderMissingLetters,
  word_sort: renderWordSort,
  heart_word_spotlight: renderHeartWordSpotlight,
  phrase_dictation: renderPhraseDictation,
  sentence_scribe: renderSentenceScribe,
  bd_ninja: renderBdNinja,
};

export function renderExercise(item, onSubmit) {
  const renderer = RENDERERS[item.type] || renderEchoDictation;
  return renderer(item, onSubmit);
}
