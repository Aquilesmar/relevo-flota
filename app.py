import os
from pathlib import Path
from flask import Flask, Response, jsonify, render_template, request
import requests
from assistant_api import ask, configured
from workshop import ROOT, Workshop, bundled


def create_app(database=None):
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 8192
    store = Workshop(database or ROOT / "instance" / "shift.sqlite3")

    @app.get("/")
    def dashboard():
        return render_template("index.html", shift=store.shift(), metrics=bundled("evaluation.json"),
                               guides=store.guides.values(), claude=configured())

    @app.get("/api/turno")
    def shift():
        return jsonify(store.shift())

    @app.get("/api/casos/<case_id>")
    def case(case_id):
        if case_id not in store.cases:
            return jsonify(error="Caso desconocido."), 404
        return jsonify(store.cases[case_id])

    @app.post("/api/ordenes")
    def assign():
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or not isinstance(data.get("id"), str):
            return jsonify(error="Falta el identificador del caso."), 400
        try:
            created = store.assign(data["id"])
        except ValueError as exc:
            return jsonify(error=str(exc)), 409
        return jsonify(created=created, shift=store.shift()), 201 if created else 200

    @app.get("/api/parte")
    def report():
        return Response(store.handover(), mimetype="text/plain")

    @app.post("/api/asistente")
    def assistant():
        data = request.get_json(silent=True)
        question = data.get("pregunta") if isinstance(data, dict) else None
        if not isinstance(question, str) or not 1 <= len(question.strip()) <= 750:
            return jsonify(error="Escribí una pregunta de hasta 750 caracteres."), 400
        if not configured():
            return jsonify(error="Integración de Claude sin configurar."), 503
        try:
            return jsonify(ask(store, question))
        except (ValueError, KeyError, TypeError, requests.RequestException):
            return jsonify(error="No se obtuvo una respuesta verificable de Claude. La cola sigue disponible."), 502

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=int(os.getenv("PORT", "5050")))

