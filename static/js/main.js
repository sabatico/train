// Boot + view router + session loop (ADR-010). Single-page: swaps home → session
// → reward inside #app. Server owns all real state; views are dumb re-renders.

import { el, mount } from "./dom.js";
import { api } from "./api.js";
import * as speech from "./speech.js";
import { renderExercise } from "./exercises.js";
import { showCorrection } from "./correction.js";

const root = document.getElementById("app");

// ---------------- home ----------------
function renderHome() {
  const start = el("button", {
    class: "sq-btn sq-btn--primary sq-btn--hero",
    text: "Start!",
    attrs: { type: "button" },
    on: { click: beginSession },
  });
  mount(root, el("div", { class: "sq-screen" }, [
    el("div", { class: "sq-mascot sq-mascot--bob", text: "🐼" }),
    el("h1", { class: "sq-greeting", text: "Hi! Ready for today's quest?" }),
    start,
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
  mount(root, el("div", { class: "sq-screen" }, [
    progressDots(view.total_items, view.cursor),
    card,
    el("div", { class: "sq-mascot", text: "🐼" }),
  ]));
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

// ---------------- reward ----------------
async function finishSession() {
  const r = await api.finish();
  const bits = [
    el("div", { class: "sq-mascot", text: "🎉" }),
    el("div", { class: "sq-reward-stars", text: `⭐ ${r.stars || 0}` }),
    el("p", { class: "sq-reward-note", text: `${r.correct_first_try}/${r.total_items} on the first try!` }),
    el("p", { class: "sq-explain", text: `Level ${r.level} · ${r.level_name}` }),
  ];
  if (r.hatched && r.hatched.length) {
    bits.push(el("p", { class: "sq-reward-note", text: "Something hatched! 🥚→🐣" }));
  }
  bits.push(el("button", {
    class: "sq-btn sq-btn--primary",
    text: "Yay! Done",
    attrs: { type: "button" },
    on: { click: renderHome },
  }));
  mount(root, el("div", { class: "sq-screen" }, bits));
}

renderHome();
