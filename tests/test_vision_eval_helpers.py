"""Offline tests for vision evaluation helpers."""

from pathlib import Path

from scripts.vision_eval_helpers import (
    PhotoCase,
    classify_from_text,
    cosine_similarity,
    has_hedging_language,
    load_manifest_csv,
    rank_by_embedding,
    retrieval_accuracy,
    run_text_classifier_baseline,
    score_prompt_variant,
    summarize_predictions,
    top1_label_from_neighbors,
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


def test_embedding_retrieval_helpers():
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert cosine_similarity([], [1.0]) == 0.0

    gallery = [
        ("a", [1.0, 0.0, 0.0]),
        ("b", [0.9, 0.1, 0.0]),
        ("c", [0.0, 1.0, 0.0]),
    ]
    ranked = rank_by_embedding([1.0, 0.0, 0.0], gallery, top_k=2)
    assert [item_id for item_id, _ in ranked] == ["a", "b"]

    labels = {"a": "healthy", "b": "healthy", "c": "disease_suspected"}
    assert top1_label_from_neighbors(ranked, labels) == "healthy"

    metrics = retrieval_accuracy(
        queries=[("q1", [1.0, 0.0, 0.0], "healthy")],
        gallery=gallery,
        label_by_id=labels,
        top_k=2,
    )
    assert metrics["n"] == 1
    assert metrics["accuracy"] == 1.0
    assert metrics["rows"][0]["pred_label"] == "healthy"
