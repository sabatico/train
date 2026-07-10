// Boot + view router + session loop (ADR-010). Single-page: swaps home → session
// → reward inside #app. Server owns all real state; views are dumb re-renders.

import { el, mount } from "./dom.js";
import { api } from "./api.js";
import * as speech from "./speech.js";
import { renderExercise } from "./exercises.js";
import { showCorrection } from "./correction.js";

const root = document.getElementById("app");

// ---- read-aloud: a speak button on every screen ----
// Collects the meaningful text of the current view (prompts, teach text,
// explanations, words) + anything she has typed, and reads it in the kid voice.
function screenText() {
  const seen = new Set();
  const parts = [];
  root
    .querySelectorAll(
      ".sq-greeting, .sq-card__instruction, .sq-explain, .sq-word, .sq-word--xl, .sq-reward-note, .sq-card--teach .sq-word"
    )
    .forEach((el) => {
      const t = el.textContent.trim();
      if (t && !seen.has(t)) {
        seen.add(t);
        parts.push(t);
      }
    });
  root.querySelectorAll("input").forEach((i) => {
    const v = i.value.trim();
    if (v) parts.push(`you wrote: ${v}`);
  });
  return parts.join(". ");
}

function installSpeakButton() {
  const fab = el("button", {
    class: "sq-speak-fab",
    html: "🔊",
    attrs: { type: "button", "aria-label": "read this page aloud" },
    on: {
      click: () => {
        speech.unlock();
        const t = screenText();
        if (t) speech.speakText(t);
      },
    },
  });
  document.body.appendChild(fab);
}

// ---------------- home (streak, level, mission — ADR-014 §6) ----------------
async function renderHome() {
  let home = null;
  try { home = await (await fetch("/api/home")).json(); } catch { /* offline-safe */ }
  const name = home && home.display_name && home.display_name !== "friend" ? ` ${home.display_name}` : "";
  const kids = [
    el("div", { class: "sq-mascot sq-mascot--bob", text: "🐼" }),
    el("h1", { class: "sq-greeting", text: `Hi${name}! Ready for today's quest?` }),
  ];
  if (home) {
    const chips = el("div", { class: "sq-row" }, [
      el("span", { class: "sq-chip sq-chip--star", text: `🔥 ${home.streak.count}-day streak` }),
      el("span", { class: "sq-chip sq-chip--badge", text: `⭐ Lv ${home.level} · ${home.level_name}` }),
    ]);
    kids.push(chips);
    if (home.mission) {
      kids.push(el("span", { class: "sq-chip sq-chip--pink", text: `Today: ${home.mission.label} ✨` }));
    }
  }
  kids.push(el("button", {
    class: "sq-btn sq-btn--primary sq-btn--hero",
    text: "Start!",
    attrs: { type: "button" },
    on: { click: beginSession },
  }));
  kids.push(el("button", {
    class: "sq-btn sq-btn--quiet",
    text: "🥚 My Collection",
    attrs: { type: "button" },
    on: { click: renderCollection },
  }));
  mount(root, el("div", { class: "sq-screen" }, kids));
}

// ---------------- collection shelf ----------------
async function renderCollection() {
  let home = null;
  try { home = await (await fetch("/api/home")).json(); } catch { /* ignore */ }
  const rows = el("div", { class: "sq-row" });
  (home ? home.collection : []).forEach((c) => {
    rows.appendChild(
      el("div", { class: "sq-stack sq-creature" }, [
        el("div", { class: "sq-emoji-prompt", text: c.hatched ? "🐣" : "🥚" }),
        el("div", { class: "sq-creature__label", text: c.hatched ? c.label : "?" }),
      ])
    );
  });
  mount(root, el("div", { class: "sq-screen" }, [
    el("h1", { class: "sq-greeting", text: "My Collection" }),
    el("p", { class: "sq-explain", text: "Master a pattern to hatch its friend!" }),
    rows,
    el("button", {
      class: "sq-btn sq-btn--primary",
      text: "Back",
      attrs: { type: "button" },
      on: { click: renderHome },
    }),
  ]));
}

// ---------------- session ----------------
function progressDots(total, cursor) {
  const dots = el("div", { class: "sq-dots" });
  for (let i = 0; i < total; i++) {
    let cls = "sq-dot";
    if (i < cursor) cls += " sq-dot--done";
    else if (i === cursor) cls += " sq-dot--current";
    dots.appendChild(el("span", { class: cls }));
  }
  return dots;
}

function renderTeach(view, onContinue) {
  const teach = view.teach;
  mount(root, el("div", { class: "sq-screen" }, [
    el("div", { class: "sq-card sq-card--teach" }, [
      el("p", { class: "sq-card__instruction", text: "Today's pattern" }),
      el("div", { class: "sq-word sq-word--xl", text: (teach.examples[0] || "") }),
      el("p", { class: "sq-explain", text: teach.text }),
      el("button", {
        class: "sq-btn sq-btn--star",
        text: "Got it!",
        attrs: { type: "button" },
        on: { click: onContinue },
      }),
    ]),
  ]));
}

function renderItem(view) {
  if (view.done || !view.item) return finishSession();
  const card = el("div", { class: "sq-card" });
  const exercise = renderExercise(view.item, (attempt) =>
    handleAnswer(view.item.item_id, attempt)
  );
  card.appendChild(exercise);
  const screen = [progressDots(view.total_items, view.cursor), card];
  if (view.slot === "challenge") {
    // the challenge caps the session and is skippable without penalty (PLAN §7)
    card.prepend(el("span", { class: "sq-chip sq-chip--star", text: "⭐ Challenge!" }));
    screen.push(el("button", {
      class: "sq-btn sq-btn--ghost",
      text: "skip for today",
      attrs: { type: "button" },
      on: {
        click: async () => { await fetch("/api/session/skip", { method: "POST" }); advance(); },
      },
    }));
  }
  screen.push(el("div", { class: "sq-mascot", text: "🐼" }));
  mount(root, el("div", { class: "sq-screen" }, screen));
  if (exercise.focusFirst) setTimeout(exercise.focusFirst, 50);
}

async function handleAnswer(itemId, attempt) {
  const res = await api.answer(itemId, attempt, "first");
  if (res.next === "retry") {
    showCorrection(
      root,
      res.reveal,
      (retry) => api.answer(itemId, retry, "retry"),
      advance
    );
  } else {
    advance();
  }
}

async function advance() {
  const view = await api.getItem();
  if (view.error || view.done || !view.item) return finishSession();
  renderItem(view);
}

async function beginSession() {
  speech.unlock();
  const view = await api.startSession();
  if (view.teach) renderTeach(view, () => renderItem(view));
  else renderItem(view);
}

// ---------------- reward (level progress, hatch, streak — ADR-014 §6) ----------------
async function finishSession() {
  const r = await api.finish();
  let home = null;
  try { home = await (await fetch("/api/home")).json(); } catch { /* ignore */ }
  const bits = [
    el("div", { class: "sq-mascot", text: "🎉" }),
    el("div", { class: "sq-reward-stars", text: `⭐ ${r.stars || 0}` }),
    el("p", { class: "sq-reward-note", text: `${r.correct_first_try}/${r.total_items} on the first try!` }),
  ];
  if (home) {
    const pct = Math.min(100, Math.round((home.xp / Math.max(1, home.xp_next_level)) * 100));
    const fill = el("div", { class: "sq-meter__fill" });
    fill.style.setProperty("--sq-meter-pct", `${pct}%`);
    bits.push(el("p", { class: "sq-explain", text: `Level ${home.level} · ${home.level_name} — ${home.xp_next_level - home.xp} ⭐ to the next level!` }));
    bits.push(el("div", { class: "sq-meter" }, [fill]));
    bits.push(el("span", { class: "sq-chip sq-chip--star", text: `🔥 ${home.streak.count}-day streak` }));
  }
  if (r.hatched && r.hatched.length) {
    bits.push(el("p", { class: "sq-reward-note", text: `Something hatched! 🥚→🐣 (${r.hatched.join(", ")})` }));
  }
  if (r.newly_introduced && r.newly_introduced.length) {
    bits.push(el("span", { class: "sq-chip sq-chip--pink", text: "✨ New pattern unlocked!" }));
  }
  bits.push(el("button", {
    class: "sq-btn sq-btn--primary",
    text: "Yay! Done",
    attrs: { type: "button" },
    on: { click: renderHome },
  }));
  mount(root, el("div", { class: "sq-screen" }, bits));
}

installSpeakButton();
renderHome();
