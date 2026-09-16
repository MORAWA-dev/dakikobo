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


@app.get("/healthz")
def healthz():
    # Readiness probe for the rehearsal runner; no provider or model is touched.
    return jsonify(status="ok")


@app.get("/broken-audio.mp3")
def broken_audio():
    # Declared as audio but carries an undecodable payload, so the browser fires
    # a media 'error' event promptly and deterministically in headless Chromium
    # (a 404 file never triggers the error event in the headless media stack).
    from flask import Response

    return Response(b"not-a-real-mp3", mimetype="audio/mpeg")


@app.post("/ask")
def ask():
    # Synthetic answer only. The audio_url points at an undecodable payload so
    # the browser exercises the audio-failure recovery path deterministically.
    return jsonify(
        answer="Conseil synthétique : le texte reste disponible.",
        sources=[],
        confidence="Faible",
        audio_url="/broken-audio.mp3",
    )


if __name__ == "__main__":
    import os

    app.run(
        host="127.0.0.1",
        port=int(os.environ.get("BROWSER_FIXTURE_PORT", "5097")),
        use_reloader=False,
    )
