"""Static frontend asset checks for demo-critical controls."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_audio_replay_control_is_wired_in_frontend_assets():
    js = (ROOT / "static/js/index.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/style.css").read_text(encoding="utf-8")

    assert "function renderAudioReplay" in js
    assert "Réécouter" in js
    assert "playAudio(response.audio_url)" in js
    assert ".audio-replay" in css
