"""Create the standalone recruiter demo using the dashboard's own template."""
import json
from flask import Flask, render_template
from workshop import CAPACITY, ROOT, bundled


def build():
    queue = sorted((r for r in bundled("shift.json") if r["flagged"]), key=lambda r: -r["score"])
    shift = dict(total=len(bundled("shift.json")), free=CAPACITY, capacity=CAPACITY, assigned=[], queue=queue)
    with Flask(__name__).test_request_context():
        html = render_template("index.html", shift=shift, metrics=bundled("evaluation.json"),
                               guides=bundled("procedures.json"), claude=False)
    css = (ROOT / "static/app.css").read_text(encoding="utf-8")
    script = (ROOT / "static/preview.js").read_text(encoding="utf-8")
    html = html.replace('<link rel="stylesheet" href="/static/app.css">', f"<style>{css}</style>")
    html = html.replace('<script src="/static/app.js"></script>',
                        f'<script type="application/json" id="shift">{json.dumps(shift)}</script><script>{script}</script>')
    html = html.replace("Modo local · Guías y parte disponibles. Las preguntas abiertas se habilitan al conectar Claude.",
                        "Demo en tu navegador. Las asignaciones se reinician al recargar. La aplicación Python ofrece consultas a Claude.")
    destination = ROOT / "docs" / "index.html"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    build()

