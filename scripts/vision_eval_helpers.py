"""Helpers for the DakiKobo leaf-photo evaluation lab.

Importable from Colab notebooks and unit tests. No network calls unless the
caller provides a Gemini client function.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable


LABELS = (
    "healthy",
    "disease_suspected",
    "pest_damage",
    "not_a_plant",
    "blurry",
    "unknown",
)

PROMPTS = {
    "hedged_v1": (
        "Tu es un assistant agricole prudent pour le Burkina Faso. "
        "Décris seulement ce qui est visible. Utilise un langage d'hypothèse "
        "(\"il pourrait s'agir de…\"). Si la photo est floue ou n'est pas une plante, "
        "dis-le clairement. Ce n'est pas un diagnostic. Réponds en français simple."
    ),
    "strict_unclear_v1": (
        "Tu es un assistant agricole prudent. "
        "Si la photo n'est pas nette, de face, et clairement une feuille de culture, "
        "réponds que tu ne peux pas conclure et demande une meilleure photo. "
        "Sinon, propose au plus 2 hypothèses prudentes. Français simple. Pas de diagnostic."
    ),
}


@dataclass
class PhotoCase:
    case_id: str
    image_path: str
    crop: str = ""
    gold_label: str = "unknown"
    gold_notes: str = ""
    source: str = "phone_photo"
    split: str = "eval"


@dataclass
class ModelPrediction:
    case_id: str
    model_name: str
    pred_label: str
    raw_text: str
    latency_ms: float = 0.0
    error: str = ""


def classify_from_text(text: str) -> str:
    """Map free-form French screening text to a coarse evaluation label."""
    t = (text or "").lower()
    if any(k in t for k in ("flou", "pas nette", "illisible", "reprenez", "pas de conclusion")):
        return "blurry"
    if any(
        k in t
        for k in (
            "pas une plante",
            "pas une feuille",
            "n'est pas une feuille",
            "n’est pas une feuille",
            "objet",
            "personne",
            "selfie",
        )
    ):
        return "not_a_plant"
    if any(k in t for k in ("sain", "aucune tache", "pas de symptôme", "pas de symptome", "plante saine")):
        return "healthy"
    if any(k in t for k in ("ravageur", "insecte", "morsure", "dégât", "degat", "chenille")):
        return "pest_damage"
    if any(k in t for k in ("maladie", "champignon", "tache", "pourrait", "chlorose", "rouille")):
        return "disease_suspected"
    return "unknown"


def accuracy(y_true: Iterable[str], y_pred: Iterable[str]) -> float:
    pairs = [(t, p) for t, p in zip(y_true, y_pred) if t and p]
    if not pairs:
        return 0.0
    return sum(t == p for t, p in pairs) / len(pairs)


def safe_refusal_rate(rows: list[dict]) -> float | None:
    """Share of blurry/not_a_plant gold cases predicted as blurry/not_a_plant/unknown."""
    hard = [r for r in rows if r.get("gold_label") in {"blurry", "not_a_plant"}]
    if not hard:
        return None
    ok = sum(1 for r in hard if r.get("pred_label") in {"blurry", "not_a_plant", "unknown"})
    return ok / len(hard)


def load_manifest_csv(path: str | Path) -> list[PhotoCase]:
    import csv

    path = Path(path)
    cases: list[PhotoCase] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cases.append(
                PhotoCase(
                    case_id=(row.get("case_id") or "").strip(),
                    image_path=(row.get("image_path") or "").strip(),
                    crop=(row.get("crop") or "").strip(),
                    gold_label=(row.get("gold_label") or "unknown").strip() or "unknown",
                    gold_notes=(row.get("gold_notes") or "").strip(),
                    source=(row.get("source") or "phone_photo").strip(),
                    split=(row.get("split") or "eval").strip(),
                )
            )
    return [c for c in cases if c.case_id and c.image_path]


def write_manifest_csv(path: str | Path, cases: list[PhotoCase]) -> None:
    import csv

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "case_id",
        "image_path",
        "crop",
        "gold_label",
        "gold_notes",
        "source",
        "split",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for case in cases:
            writer.writerow(asdict(case))


def summarize_predictions(rows: list[dict]) -> dict:
    return {
        "n": len(rows),
        "accuracy": accuracy(
            [r.get("gold_label", "") for r in rows],
            [r.get("pred_label", "") for r in rows],
        ),
        "safe_refusal_rate": safe_refusal_rate(rows),
        "pred_label_counts": {
            label: sum(1 for r in rows if r.get("pred_label") == label) for label in LABELS
        },
    }


def write_markdown_report(
    path: str | Path,
    title: str,
    metrics: dict,
    notes: str = "",
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {title}",
        "",
        "## Metrics",
        "```json",
        json.dumps(metrics, indent=2, ensure_ascii=False),
        "```",
        "",
        "## Notes",
        notes or "_Add qualitative failures here._",
        "",
        "## Ship / no-ship checklist",
        "- [ ] Beats Gemini production-like prompt on real phone photos",
        "- [ ] Safe on blurry / not-a-plant negatives",
        "- [ ] French hedging language reviewed by a human",
        "- [ ] No chemical product invention",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def run_text_classifier_baseline(
    cases: list[PhotoCase],
    text_by_case_id: dict[str, str],
    model_name: str = "text_heuristic",
) -> list[ModelPrediction]:
    """Score pre-collected model texts with the shared label mapper."""
    preds: list[ModelPrediction] = []
    for case in cases:
        text = text_by_case_id.get(case.case_id, "")
        preds.append(
            ModelPrediction(
                case_id=case.case_id,
                model_name=model_name,
                pred_label=classify_from_text(text),
                raw_text=text,
            )
        )
    return preds


def has_hedging_language(text: str) -> bool:
    """True if the French text keeps a cautious hypothesis style."""
    t = (text or "").lower()
    return bool(
        re.search(
            r"pourrait|possible|semble|il se peut|hypothèse|hypothese|à confirmer|a confirmer|pas un diagnostic",
            t,
        )
    )


def score_prompt_variant(
    cases: list[PhotoCase],
    generate_fn: Callable[[PhotoCase, str], str],
    prompt_name: str,
) -> list[dict]:
    """Run a prompt variant callable over cases; returns joinable result rows."""
    prompt = PROMPTS.get(prompt_name, PROMPTS["hedged_v1"])
    rows: list[dict] = []
    for case in cases:
        try:
            text = generate_fn(case, prompt)
            pred = classify_from_text(text)
            err = ""
        except Exception as exc:  # notebook/demo resilience
            text = ""
            pred = "unknown"
            err = type(exc).__name__
        rows.append(
            {
                "case_id": case.case_id,
                "gold_label": case.gold_label,
                "pred_label": pred,
                "crop": case.crop,
                "prompt": prompt_name,
                "hedged": has_hedging_language(text),
                "raw_text": text[:500],
                "error": err,
            }
        )
    return rows
