// The only fetch layer to /api/* (ADR-010). The server is authoritative for
// session state and grading; the client never decides correctness.

async function post(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  return res.json();
}

async function get(path) {
  const res = await fetch(path);
  return res.json();
}

export const api = {
  startSession: () => post("/api/session/start"),
  getItem: () => get("/api/session/item"),
  answer: (itemId, attempt, phase = "first") =>
    post("/api/session/answer", { item_id: itemId, attempt, phase }),
  finish: () => post("/api/session/finish"),
  skills: () => get("/api/skills"),
};
