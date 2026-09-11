"""Isolated frontend fixture for browser acceptance checks; never calls providers."""

from pathlib import Path

from flask import Flask, jsonify, render_template


ROOT = Path(__file__).resolve().parents[1]
app = Flask(
    __name__,
    static_folder=str(ROOT / "static"),
    template_folder=str(ROOT / "templates"),
)


@app.get("/")
def index():
    return render_template(
        "index.html",
        journal_retention_days=90,
        search_engine_indexing_enabled=False,
    )


@app.get("/registry")
def registry():
    return jsonify(crops=[], places=[])


@app.get("/crop-labels")
def crop_labels():
    return jsonify(crops=[])


@app.post("/ask")
def ask():
    return jsonify(
        answer="Conseil synthétique : le texte reste disponible.",
        sources=[],
        confidence="Faible",
        audio_url="/static/audio/test-expired.mp3",
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5097, use_reloader=False)
