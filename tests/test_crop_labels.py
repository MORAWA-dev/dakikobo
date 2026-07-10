"""Tests for experimental crop label glossary."""

from core.crop_labels import french_label, load_crop_labels, local_labels_ready


def test_load_primary_crops():
    data = load_crop_labels()
    ids = {c["id"] for c in data["crops"]}
    assert {"mil", "sorgho", "mais", "niebe", "arachide"} <= ids
    assert data["meta"]["primary_language"] == "fr"


def test_french_labels():
    assert french_label("mil") == "Mil"
    assert "mil" in french_label("mil", simple=True).lower()
    assert french_label("unknown_crop") == "unknown_crop"


def test_local_labels_empty_until_reviewed():
    # Provisional stubs must stay empty so UI does not show invented terms.
    for crop_id in ("mil", "sorgho", "mais", "niebe", "arachide"):
        assert local_labels_ready(crop_id) is False
