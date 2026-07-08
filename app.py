"""Spell Quest — Flask app (ADR-001) and the tenancy-shaped route namespaces
(ADR-004): kid app under /app + /api, parent under /parent. Stateless per request
(ADR-004/009) — all state persists via engine.store.

This is the skeleton: /healthz plus placeholder shells. Session endpoints and the
UI land in B6/B7 against the frozen contracts (ADR-005/009).
"""
from __future__ import annotations

import os

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect

from engine import store

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
        # Placeholder until the SPA shell lands (B7 / ADR-010).
        return "<h1>Spell Quest</h1><p>the kid app shell will render here.</p>"

    @app.get("/parent")
    def parent_dashboard():
        # Placeholder until the parent dashboard lands (PAR-01).
        return "<h1>Spell Quest — grown-ups</h1><p>dashboard coming soon.</p>"

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
