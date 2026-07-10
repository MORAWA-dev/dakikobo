"""Offline tests for vision evaluation helpers."""

from pathlib import Path

from scripts.vision_eval_helpers import (
    PhotoCase,
    classify_from_text,
    has_hedging_language,
    load_manifest_csv,
    run_text_classifier_baseline,
    score_prompt_variant,
    summarize_predictions,
    write_manifest_csv,
    write_markdown_report,
)


def test_classify_from_text_covers_main_labels():
    assert classify_from_text("La photo est floue, reprenez la photo.") == "blurry"
    assert classify_from_text("Ce n'est pas une feuille de culture.") == "not_a_plant"
    assert classify_from_text("La plante semble saine sans tache.") == "healthy"
    assert classify_from_text("Dégâts possibles de ravageurs sur la feuille.") == "pest_damage"
    assert classify_from_text("Il pourrait s'agir d'une maladie foliaire.") == "disease_suspected"
    assert classify_from_text("Bonjour") == "unknown"


def test_manifest_roundtrip_and_summary(tmp_path: Path):
    cases = [
        PhotoCase("b1", "images/blur.jpg", gold_label="blurry"),
        PhotoCase("d1", "images/mais.jpg", crop="maïs", gold_label="disease_suspected"),
    ]
    path = tmp_path / "manifest.csv"
    write_manifest_csv(path, cases)
    loaded = load_manifest_csv(path)
    assert len(loaded) == 2
    assert loaded[0].case_id == "b1"

    preds = run_text_classifier_baseline(
        loaded,
        {
            "b1": "Image floue, reprenez.",
            "d1": "Il pourrait s'agir d'une maladie.",
        },
    )
    rows = [
        {
            "gold_label": c.gold_label,
            "pred_label": p.pred_label,
        }
        for c, p in zip(loaded, preds)
    ]
    metrics = summarize_predictions(rows)
    assert metrics["n"] == 2
    assert metrics["accuracy"] == 1.0
    assert metrics["safe_refusal_rate"] == 1.0

    report = tmp_path / "report.md"
    write_markdown_report(report, "Test", metrics, notes="ok")
    text = report.read_text(encoding="utf-8")
    assert "Ship / no-ship" in text
    assert "accuracy" in text


def test_score_prompt_variant_and_hedging():
    cases = [PhotoCase("x1", "a.jpg", gold_label="disease_suspected")]

    def gen(case, prompt):
        assert "Burkina" in prompt or "prudente" in prompt
        return "Il pourrait s'agir d'une maladie. Ceci n'est pas un diagnostic."

    rows = score_prompt_variant(cases, gen, "hedged_v1")
    assert rows[0]["pred_label"] == "disease_suspected"
    assert rows[0]["hedged"] is True
    assert has_hedging_language(rows[0]["raw_text"])
