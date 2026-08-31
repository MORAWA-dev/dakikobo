import json
from pathlib import Path

from core.fertilizer import DISCLAIMER, _CROP_LABEL, _RECOMMENDATIONS


ROOT = Path(__file__).resolve().parents[1]


def test_offline_fertilizer_table_matches_authoritative_python_data():
    offline = json.loads(
        (ROOT / "static/data/fertilizer.json").read_text(encoding="utf-8")
    )

    assert offline["disclaimer"] == DISCLAIMER
    assert set(offline["crops"]) == set(_RECOMMENDATIONS)
    for crop_id, recommendation in _RECOMMENDATIONS.items():
        assert offline["crops"][crop_id]["label"] == _CROP_LABEL[crop_id]
        assert offline["crops"][crop_id]["lines"] == recommendation["lines"]
        assert offline["crops"][crop_id]["sources"] == recommendation["sources"]


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
