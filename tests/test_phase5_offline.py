import json
from pathlib import Path

from core.fertilizer import build_offline_fertilizer_payload


ROOT = Path(__file__).resolve().parents[1]


def test_offline_fertilizer_table_matches_authoritative_python_data():
    offline = json.loads(
        (ROOT / "static/data/fertilizer.json").read_text(encoding="utf-8")
    )

    assert offline == build_offline_fertilizer_payload()


def test_pwa_assets_are_wired_for_root_scope_and_offline_ask_fallback():
    html = (ROOT / "templates/index.html").read_text(encoding="utf-8")
    js = (ROOT / "static/js/index.js").read_text(encoding="utf-8")
    worker = (ROOT / "static/sw.js").read_text(encoding="utf-8")

    assert 'rel="manifest"' in html
    assert "Mode hors ligne — dernières réponses enregistrées" in html
    assert "navigator.serviceWorker.register('/sw.js', { scope: '/' })" in js
    assert "event.request.method === 'POST' && url.pathname === '/ask'" in worker
    assert "offlineFertilizer(formData)" in worker
    assert "'/registry'" in worker
    assert "url.origin === self.location.origin" not in worker
    assert "SHELL.indexOf(url.pathname)" in worker


def test_render_module_contains_no_network_transport():
    render_js = (ROOT / "static/js/render.js").read_text(encoding="utf-8")

    assert "$.ajax" not in render_js
    assert "$.post" not in render_js
    assert "api.submitFeedback" in render_js
    assert "api.submitOutcome" in render_js
