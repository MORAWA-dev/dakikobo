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
    js = (ROOT / "static/js/render.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/style.css").read_text(encoding="utf-8")

    assert "éditeur, année, statut de revue et portée" in html
    assert "function sourceMetaItems" in js
    assert "src.publisher" in js
    assert "src.review_status" in js
    assert "src.scope" in js
    assert "Portée et limites" in js
    assert "function safeSourceUrl" in js
    assert ".source-meta" in css
    assert ".source-scope" in css
    assert ".source-title-link" in css


def test_media_privacy_note_is_visible():
    html = (ROOT / "templates/index.html").read_text(encoding="utf-8")
    css = (ROOT / "static/css/style.css").read_text(encoding="utf-8")

    assert "Confidentialité" in html
    assert 'id="mediaPrivacyNote"' in html
    assert "Photo et dictée servent seulement à l'analyse" in html
    assert "Évitez les visages, noms, numéros" in html
    assert ".media-privacy-note" in css


def test_keyboard_and_screen_reader_landmarks_are_wired():
    html = (ROOT / "templates/index.html").read_text(encoding="utf-8")
    css = (ROOT / "static/css/style.css").read_text(encoding="utf-8")
    js = (ROOT / "static/js/index.js").read_text(encoding="utf-8")

    assert 'class="skip-link" href="#mainContent"' in html
    assert 'id="mainContent"' in html
    assert 'role="dialog"' in html and 'id="journalPanel"' in html
    assert 'aria-expanded="false"' in html.split('id="journalToggle"', 1)[1].split(">", 1)[0]
    assert 'aria-label="Culture pour le conseil sol et engrais"' in html
    assert 'aria-label="Lieu pour le conseil sol et engrais"' in html
    assert "function trapDialogFocus" in js
    assert "setJournalOpen" in js
    assert ".skip-link" in css
    assert "textarea:focus-visible" in css


def test_landing_strip_is_wired_in_frontend_assets():
    html = (ROOT / "templates/index.html").read_text(encoding="utf-8")
    css = (ROOT / "static/css/style.css").read_text(encoding="utf-8")
    js = (ROOT / "static/js/index.js").read_text(encoding="utf-8")

    assert 'id="landingStrip"' in html
    assert "Assistant agricole prudent" in html
    assert "mil" in html and "sorgho" in html and "niébé" in html
    assert ".landing-strip" in css
    assert ".landing-lead" in css
    assert "Pourquoi" in js
    assert "À éviter" in js
    assert "Conseil engrais" in js
    assert "response.case" in js
    # Chat-first layout: context and examples start collapsed.
    assert 'aria-expanded="false"' in html
    assert 'id="examplesToggle"' in html
    assert "function setExamplesOpen" in js
    assert "setFieldContextOpen(false)" in js
    assert "setExamplesOpen(false)" in js


def test_uncertain_badge_and_known_limits_are_wired():
    html = (ROOT / "templates/index.html").read_text(encoding="utf-8")
    css = (ROOT / "static/css/style.css").read_text(encoding="utf-8")
    js = (ROOT / "static/js/index.js").read_text(encoding="utf-8")

    assert "Limites connues" in html
    assert "Je ne peux pas confirmer" in html
    assert ".case-badge.uncertain" in css


def test_simple_french_toggle_is_wired():
    html = (ROOT / "templates/index.html").read_text(encoding="utf-8")
    css = (ROOT / "static/css/style.css").read_text(encoding="utf-8")
    js = (ROOT / "static/js/index.js").read_text(encoding="utf-8")

    assert 'id="simpleFrenchToggle"' in html
    assert "Français simple" in html
    assert "function isSimpleFrenchEnabled" in js
    assert "simple_french" in js
    assert ".field-simple-french" in css


def test_crop_labels_client_is_wired():
    index_js = (ROOT / "static/js/index.js").read_text(encoding="utf-8")
    api_js = (ROOT / "static/js/api.js").read_text(encoding="utf-8")
    assert "function applyCropLabels" in index_js
    assert "/crop-labels" in api_js


def test_field_context_local_storage_is_wired():
    js = (ROOT / "static/js/index.js").read_text(encoding="utf-8")
    render_js = (ROOT / "static/js/render.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/style.css").read_text(encoding="utf-8")
    html = (ROOT / "templates/index.html").read_text(encoding="utf-8")

    assert "dakikobo_field_context_v1" in js
    assert "function saveFieldContextToStorage" in js
    assert "function loadFieldContextFromStorage" in js
    assert "loadFieldContextFromStorage()" in js
    assert "fr_simple" in js
    assert "examples-toggle" in css or "examplesToggle" in html
    assert "Exemples rapides" in html
    assert "case-badge uncertain" in js
    assert "Non confirmé" in js
    # Compact answer cards: lead paragraph, clean lists, collapsed sources.
    assert "case-lead" in js
    assert "function cleanDisplayText" in render_js
    assert "function renderCompactSources" in js
    assert "Ce que vous pouvez faire maintenant" in js
    assert "case-weather-line" in js
    assert "diagnostic-case-compact" in js
    assert ".case-lead" in css
    assert ".sources-details" in css
    assert ".case-meta-line" in css
    # Multi-turn: short follow-ups send prior_question so topic is kept.
    assert "prior_question" in js
    assert "lastUserQuestion" in js
    assert "looksLikeShortFollowup" in js
    assert "Sujet :" in js


def test_text_field_context_panel_is_wired():
    html = (ROOT / "templates/index.html").read_text(encoding="utf-8")
    css = (ROOT / "static/css/style.css").read_text(encoding="utf-8")
    js = (ROOT / "static/js/index.js").read_text(encoding="utf-8")

    assert 'id="fieldContextPanel"' in html
    assert 'id="fieldCrop"' in html
    assert 'id="fieldStage"' in html
    assert 'id="fieldLocationSelect"' in html
    assert 'id="fieldLocationCustom"' in html
    assert "Contexte parcelle" in html or "1. Contexte parcelle" in html
    assert ".field-context-panel" in css
    assert "function getFieldContext" in js
    assert "function getFieldLocationValue" in js
    assert "function syncToolsFromFieldLocation" in js
    assert "setFieldContextOpen(false)" in js
    assert "growth_stage: ctx.growth_stage" in js
    assert "location: getFieldLocationValue()" in js
    assert "Météo" in js
    assert "weather_signals" in js
    assert "<code>/ops</code>" not in html
    # Field context appears before the chat panel in the field workflow layout.
    assert html.find('id="fieldContextPanel"') < html.find('id="chatPanel"')


def test_simple_french_does_not_replace_collapsed_context_label():
    js = (ROOT / "static/js/index.js").read_text(encoding="utf-8")
    update = js.split("function updateFieldContextToggleLabel", 1)[1].split(
        "function setExamplesOpen", 1
    )[0]
    assert "ctx.simple_french = false" in update


def test_phase_zero_frontend_regressions_are_fixed():
    render_js = (ROOT / "static/js/render.js").read_text(encoding="utf-8")
    api_js = (ROOT / "static/js/api.js").read_text(encoding="utf-8")
    index_js = (ROOT / "static/js/index.js").read_text(encoding="utf-8")

    assert "/route commerciale|march[eé]s villageois|vente de bois|→/i" in render_js
    assert "vente de bois||" not in render_js
    assert "function escapeHtml" in render_js

    type_body = render_js.split("function typeMessage", 1)[1].split("return {", 1)[0]
    assert ".html(" not in type_body
    assert "element.text(" in type_body
    assert "setInterval" not in type_body

    assert "function uploadImageForScreening(file, crop, growthStage, location, simpleFrench, question)" in api_js
    assert 'context.question || "Photo maladie"' in index_js


def test_registry_populates_all_five_dynamic_selects():
    html = (ROOT / "templates/index.html").read_text(encoding="utf-8")
    js = (ROOT / "static/js/index.js").read_text(encoding="utf-8")

    assert '<option value="ouagadougou">' not in html
    assert '<option value="maïs">' not in html
    for select_id in (
        "fieldCrop",
        "fieldLocationSelect",
        "weatherLocation",
        "soilLocation",
        "soilCrop",
    ):
        assert f'#{select_id}' in js
    assert "function populateRegistrySelects" in js
    assert "place.has_weather" in js
    assert "crop.fertilizer_supported" in js
    assert "FIELD_LOCATION_TO_WEATHER" not in js


def test_voice_input_uses_server_side_stt():
    js = (ROOT / "static/js/index.js").read_text(encoding="utf-8")

    assert "url: \"/speech\"" in js
    assert "navigator.mediaDevices.getUserMedia" in js
    assert "new MediaRecorder" in js
    assert "function startNativeSpeechRecognition" in js
    assert "La saisie vocale a échoué" not in js


def test_followup_supports_optional_after_photo():
    render_js = (ROOT / "static/js/render.js").read_text(encoding="utf-8")
    api_js = (ROOT / "static/js/api.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/style.css").read_text(encoding="utf-8")

    assert "followup-after-photo" in render_js
    assert "submitOutcome" in render_js
    assert "after_image" in api_js
    assert "/feedback/outcome" in api_js
    assert ".followup-after-photo" in css


def test_offline_outcome_queue_is_wired_and_flushed():
    """Phase D: an offline follow-up outcome is queued durably and replayed."""
    api_js = (ROOT / "static/js/api.js").read_text(encoding="utf-8")
    index_js = (ROOT / "static/js/index.js").read_text(encoding="utf-8")
    render_js = (ROOT / "static/js/render.js").read_text(encoding="utf-8")

    # A durable queue, a flush routine, and reconnection replay all exist.
    assert "dakikobo_outcome_queue_v1" in api_js
    assert "flushOutcomeQueue" in api_js
    assert "pendingOutcomeCount" in api_js
    assert "addEventListener('online'" in api_js
    # The app replays the queue on load when online.
    assert "flushOutcomeQueue" in index_js
    # The farmer is told honestly when an outcome was only queued offline.
    assert "queued" in render_js and "hors ligne" in render_js
