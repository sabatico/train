"""Spell Quest — Flask app (ADR-001) and the tenancy-shaped route namespaces
(ADR-004): kid app under /app + /api, parent under /parent. Stateless per request
(ADR-004/009) — all state persists via engine.store.

This is the skeleton: /healthz plus placeholder shells. Session endpoints and the
UI land in B6/B7 against the frozen contracts (ADR-005/009).
"""
from __future__ import annotations

import os

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request

from engine import session as session_engine, store

load_dotenv()

CONTRACT_VERSION = 1          # ADR-005 envelope version
DEFAULT_STUDENT = "default"   # v1 single student (ADR-004 seam: never assumed elsewhere)


def create_app() -> Flask:
    app = Flask(__name__)

    # Ensure the single v1 student exists (idempotent — invariant #1 safe).
    store.bootstrap_student(DEFAULT_STUDENT)

    @app.get("/healthz")
    def healthz():
        return jsonify(status="ok", contract_version=CONTRACT_VERSION, agent="deepseek")

    @app.get("/")
    def root():
        return redirect("/app")

    @app.get("/app")
    def kid_app():
        return render_template("app.html")

    @app.get("/parent")
    def parent_dashboard():
        # Placeholder until the parent dashboard lands (PAR-01).
        return "<h1>Spell Quest — grown-ups</h1><p>dashboard coming soon.</p>"

    # ---- Session API (ADR-009). Stateless per request; v1 uses DEFAULT_STUDENT. ----
    @app.post("/api/session/start")
    def api_session_start():
        return jsonify(session_engine.start_session(DEFAULT_STUDENT))

    @app.get("/api/session/item")
    def api_session_item():
        view = session_engine.get_item(DEFAULT_STUDENT)
        if view is None:
            return jsonify(error="no_active_session"), 404
        return jsonify(view)

    @app.post("/api/session/answer")
    def api_session_answer():
        body = request.get_json(silent=True) or {}
        item_id, attempt = body.get("item_id"), body.get("attempt", "")
        if not item_id:
            return jsonify(error="item_id required"), 400
        result = session_engine.submit_answer(
            DEFAULT_STUDENT, item_id, attempt, phase=body.get("phase", "first")
        )
        status = 409 if result.get("error") in {"item_mismatch", "session_complete"} else 200
        status = 404 if result.get("error") == "no_active_session" else status
        return jsonify(result), status

    @app.post("/api/session/finish")
    def api_session_finish():
        result = session_engine.finish_session(DEFAULT_STUDENT)
        return jsonify(result), (404 if result.get("error") else 200)

    @app.get("/api/skills")
    def api_skills():
        return jsonify(store.load(DEFAULT_STUDENT, "skills"))

    return app


app = create_app()


if __name__ == "__main__":
    # use_reloader=False on purpose: the app writes the child's data under data/,
    # and the file-watching reloader would restart the server mid-session (wiping
    # sessions/current.json in flight). Keep the debugger, drop the reloader.
    app.run(debug=True, use_reloader=False, port=int(os.environ.get("PORT", 5000)))
