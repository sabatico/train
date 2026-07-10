"""Spell Quest — Flask app (ADR-001) and the tenancy-shaped route namespaces
(ADR-004): kid app under /app + /api, parent under /parent. Stateless per request
(ADR-004/009) — all state persists via engine.store.

This is the skeleton: /healthz plus placeholder shells. Session endpoints and the
UI land in B6/B7 against the frozen contracts (ADR-005/009).
"""
from __future__ import annotations

import os

import hashlib
from datetime import date

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, send_file

from agent import voice
from engine import report, session as session_engine, store

load_dotenv()

CONTRACT_VERSION = 1          # ADR-005 envelope version
DEFAULT_STUDENT = "default"   # v1 single student (ADR-004 seam: never assumed elsewhere)


def _set_num(form, key, settings, cast, lo, hi):
    """Clamp-and-apply one numeric setting; ignore a missing/invalid value (an
    absent field casts None → TypeError) so a bad field never rolls back others."""
    try:
        settings[key] = max(lo, min(hi, cast(form.get(key))))
    except (TypeError, ValueError):
        pass


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
        today = date.today()
        skills_doc = store.load(DEFAULT_STUDENT, "skills")
        summary = report.skill_summary(skills_doc, today)
        logs = [
            log
            for key in store.list_session_logs(DEFAULT_STUDENT)
            if (log := store.load_session_log(DEFAULT_STUDENT, key))
        ]
        return render_template(
            "parent.html",
            summary=summary,
            weakest=report.weakest_introduced(summary),
            radar=report.radar_points(summary),
            errors=report.recent_errors(logs),
            rewards=store.load(DEFAULT_STUDENT, "rewards"),
            profile=store.load(DEFAULT_STUDENT, "profile"),
        )

    @app.post("/parent/settings")
    def parent_settings():
        profile = store.load(DEFAULT_STUDENT, "profile")
        settings = profile["settings"]
        # apply each field independently so one bad value can't discard a good one
        _set_num(request.form, "items_per_session", settings, int, 4, 20)
        _set_num(request.form, "tts_rate", settings, float, 0.5, 1.5)
        store.save(DEFAULT_STUDENT, "profile", profile)
        return redirect("/parent")

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
        if not isinstance(attempt, str):
            return jsonify(error="attempt must be a string"), 400
        result = session_engine.submit_answer(
            DEFAULT_STUDENT, item_id, attempt, phase=body.get("phase", "first")
        )
        status = 409 if result.get("error") in {"item_mismatch", "session_complete"} else 200
        status = 404 if result.get("error") == "no_active_session" else status
        status = 400 if result.get("error") == "bad_attempt" else status
        return jsonify(result), status

    @app.post("/api/session/finish")
    def api_session_finish():
        result = session_engine.finish_session(DEFAULT_STUDENT)
        return jsonify(result), (404 if result.get("error") else 200)

    @app.post("/api/session/skip")
    def api_session_skip():
        """Skip the current CHALLENGE item without penalty (PLAN §7 step 5)."""
        result = session_engine.skip_item(DEFAULT_STUDENT)
        status = 404 if result.get("error") == "no_active_session" else (
            409 if result.get("error") else 200
        )
        return jsonify(result), status

    @app.get("/api/home")
    def api_home():
        """Everything the home/reward/collection screens show (ADR-014 §6):
        streak, level, stars, today's mission, and the creature collection."""
        today = date.today()
        rewards_doc = store.load(DEFAULT_STUDENT, "rewards")
        skills_doc = store.load(DEFAULT_STUDENT, "skills")
        summary = report.skill_summary(skills_doc, today)
        weakest = report.weakest_introduced(summary, 1)
        from engine import config as engine_config

        level = rewards_doc["level"]
        xp, nxt = rewards_doc["xp"], engine_config.xp_for_level(level + 1)
        hatched = {c["skill_id"] for c in rewards_doc["collection"]}
        return jsonify(
            display_name=store.load(DEFAULT_STUDENT, "profile")["display_name"],
            streak=rewards_doc["streak"],
            level=level,
            level_name=rewards_doc["level_name"],
            stars_total=rewards_doc["stars_total"],
            xp=xp,
            xp_next_level=nxt,
            mission=weakest[0] if weakest else None,
            collection=[
                {
                    "skill_id": s["id"],
                    "label": s["label"],
                    "hatched": s["id"] in hatched,
                    "mastery": s["mastery"],
                }
                for s in summary
                if s["introduced"] or s["id"] in hatched
            ],
        )

    @app.get("/api/skills")
    def api_skills():
        return jsonify(store.load(DEFAULT_STUDENT, "skills"))

    @app.post("/api/tts")
    def api_tts():
        """Read-aloud: synthesize arbitrary on-screen text in the kid voice, cached
        by text so repeated UI copy isn't re-billed. 503 when unconfigured → the
        frontend falls back to browser TTS (ADR-013)."""
        text = ((request.get_json(silent=True) or {}).get("text") or "").strip()[:400]
        if not text:
            return jsonify(error="text required"), 400
        cache = store.DATA_ROOT / "tts_cache"
        digest = hashlib.sha1(f"{voice.VOICE}|{text}".encode("utf-8")).hexdigest()
        path = cache / f"{digest}.mp3"
        if not path.exists():
            try:
                audio = voice.synthesize(text)
            except voice.VoiceError:
                return jsonify(error="tts unavailable"), 503
            cache.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".mp3.tmp")
            tmp.write_bytes(audio)
            tmp.replace(path)
        return send_file(path, mimetype="audio/mpeg")

    return app


app = create_app()


if __name__ == "__main__":
    # use_reloader=False on purpose: the app writes the child's data under data/,
    # and the file-watching reloader would restart the server mid-session (wiping
    # sessions/current.json in flight). Keep the debugger, drop the reloader.
    app.run(debug=True, use_reloader=False, port=int(os.environ.get("PORT", 5000)))
