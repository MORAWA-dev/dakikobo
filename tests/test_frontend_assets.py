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


def test_credibility_modal_is_wired_in_frontend_assets():
    html = (ROOT / "templates/index.html").read_text(encoding="utf-8")
    js = (ROOT / "static/js/index.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/style.css").read_text(encoding="utf-8")

    assert 'id="credibilityToggle"' in html
    assert 'id="credibilityModal"' in html
    assert "Sources & limites" in html
    assert "function setCredibilityOpen" in js
    assert ".credibility-modal" in css


def test_source_cards_render_review_metadata():
    html = (ROOT / "templates/index.html").read_text(encoding="utf-8")
    js = (ROOT / "static/js/index.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/style.css").read_text(encoding="utf-8")

    assert "éditeur, année et statut de revue" in html
    assert "function sourceMetaItems" in js
    assert "src.publisher" in js
    assert "src.review_status" in js
    assert "function safeSourceUrl" in js
    assert ".source-meta" in css
    assert ".source-title-link" in css


def test_media_privacy_note_is_visible():
    html = (ROOT / "templates/index.html").read_text(encoding="utf-8")
    css = (ROOT / "static/css/style.css").read_text(encoding="utf-8")

    assert "Confidentialité" in html
    assert 'id="mediaPrivacyNote"' in html
    assert "Photo et dictée servent seulement à l'analyse" in html
    assert "Évitez les visages, noms, numéros" in html
    assert ".media-privacy-note" in css


def test_landing_strip_is_wired_in_frontend_assets():
    html = (ROOT / "templates/index.html").read_text(encoding="utf-8")
    css = (ROOT / "static/css/style.css").read_text(encoding="utf-8")
    js = (ROOT / "static/js/index.js").read_text(encoding="utf-8")

    assert 'id="landingStrip"' in html
    assert "Assistant agricole prudent" in html
    assert "mil" in html and "sorgho" in html and "niébé" in html
    assert "Essayez les exemples" in html
    assert ".landing-strip" in css
    assert ".landing-lead" in css
    assert "Pourquoi / preuves" in js
    assert "À éviter" in js
    assert "Conseil engrais" in js
    assert "response.case" in js


def test_uncertain_badge_and_known_limits_are_wired():
    html = (ROOT / "templates/index.html").read_text(encoding="utf-8")
    css = (ROOT / "static/css/style.css").read_text(encoding="utf-8")
    js = (ROOT / "static/js/index.js").read_text(encoding="utf-8")

    assert "Limites connues" in html
    assert "Je ne peux pas confirmer" in html
    assert ".case-badge.uncertain" in css
    assert "case-badge uncertain" in js
    assert "Non confirmé" in js


def test_voice_input_uses_server_side_stt():
    js = (ROOT / "static/js/index.js").read_text(encoding="utf-8")

    assert "url: \"/speech\"" in js
    assert "navigator.mediaDevices.getUserMedia" in js
    assert "new MediaRecorder" in js
    assert "function startNativeSpeechRecognition" in js
    assert "La saisie vocale a échoué" not in js
