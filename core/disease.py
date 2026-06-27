"""Leaf disease screening via Gemini Vision (REST API, no SDK dependency).

This is a *screening aid*, not a diagnosis. The prompt forces the model to:
  - refuse politely when the photo is not a clear plant/leaf image, and
  - stay hedged ("il pourrait s'agir de…") for real photos.
The code also guarantees the "ceci n'est pas un diagnostic" disclaimer is present.
"""

import base64
import json
import re

import requests

from config import GEMINI_API_KEY, GEMINI_MODEL
from core.case import build_disease_case

_API_ROOT = "https://generativelanguage.googleapis.com/v1beta"

# If the configured model is out of quota (429) or unavailable (404), fall back
# to these (known vision-capable) models in order.
_FALLBACK_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-flash-latest",
]


def _models_to_try():
    """Configured model first, then fallbacks (de-duplicated, order preserved)."""
    seen = set()
    ordered = []
    for m in [GEMINI_MODEL, *_FALLBACK_MODELS]:
        if m and m not in seen:
            seen.add(m)
            ordered.append(m)
    return ordered

# Sentinel the model returns for unusable photos (kept short for reliability).
_UNCLEAR_SENTINEL = "UNCLEAR"

UNCLEAR_MESSAGE = (
    "🤔 Je ne peux pas dire à partir de cette photo. Veuillez reprendre une "
    "photo nette de la feuille, de près et en plein jour."
)

DISCLAIMER = (
    "⚠️ Ceci n'est pas un diagnostic. Pour confirmer, montrez la plante à votre "
    "agent agricole."
)

_PROMPT = (
    "Tu es un assistant agricole pour les petits agriculteurs du Burkina Faso. "
    "Un agriculteur te montre une photo.\n\n"
    "1. Si la photo n'est PAS une image nette d'une feuille ou d'une plante "
    "cultivée (photo floue, trop sombre, ou sans rapport avec l'agriculture), "
    f"réponds UNIQUEMENT avec ce seul mot: {_UNCLEAR_SENTINEL}\n\n"
    "2. Sinon, réponds UNIQUEMENT avec un objet JSON valide, sans Markdown, "
    "avec ces clés: observations (liste de 1-2 phrases), problemes_possibles "
    "(liste prudente), actions_immediates (liste de 1-3 conseils simples), "
    "niveau_de_confiance (Faible ou Moyen), a_confirmer_par (phrase courte), "
    "reponse_courte (moins de 90 mots). "
    "Ne donne jamais de certitude et n'invente pas de produit chimique précis."
)


def _context_prompt(crop: str = "", growth_stage: str = "", location: str = "") -> str:
    parts = []
    if crop:
        parts.append(f"culture: {crop}")
    if growth_stage:
        parts.append(f"stade: {growth_stage}")
    if location:
        parts.append(f"localisation: {location}")
    if not parts:
        return _PROMPT
    context = "Contexte fourni par l'utilisateur: " + "; ".join(parts) + ".\n\n"
    return context + _PROMPT


def is_configured() -> bool:
    """True if a Gemini API key is available."""
    return bool(GEMINI_API_KEY)


def _extract_json_object(text: str) -> dict | None:
    text = text.strip()
    if not text:
        return None
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text.strip(), flags=re.IGNORECASE)
        text = re.sub(r"```$", "", text.strip())
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def _with_case(answer: str, **case_kwargs) -> dict:
    return {
        "answer": answer,
        "case": build_disease_case(
            answer=answer,
            disclaimer=DISCLAIMER,
            **case_kwargs,
        ),
    }


def screen_leaf_image(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    *,
    crop: str = "",
    growth_stage: str = "",
    location: str = "",
) -> dict:
    """Screen a leaf photo and return {"answer": str}.

    Always returns a friendly French message (never raises): handles missing key,
    network errors, rate limits (429) and unusable photos gracefully.
    """
    if not GEMINI_API_KEY:
        return _with_case(
            "La fonction d'analyse d'image n'est pas configurée "
            "(clé GEMINI_API_KEY manquante).",
            confidence="Faible",
            risk_level="Indisponible",
            crop=crop,
            growth_stage=growth_stage,
            location=location,
        )

    b64 = base64.b64encode(image_bytes).decode("utf-8")
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": _context_prompt(crop, growth_stage, location)},
                    {"inline_data": {"mime_type": mime_type, "data": b64}},
                ]
            }
        ]
    }

    resp = None
    last_status = None
    for model in _models_to_try():
        try:
            resp = requests.post(
                f"{_API_ROOT}/models/{model}:generateContent",
                params={"key": GEMINI_API_KEY},
                json=payload,
                timeout=45,
            )
        except requests.RequestException:
            return _with_case(
                "Désolé, je n'ai pas pu contacter le service d'analyse "
                "d'image. Vérifiez votre connexion et réessayez.",
                confidence="Faible",
                risk_level="Indisponible",
                crop=crop,
                growth_stage=growth_stage,
                location=location,
            )
        last_status = resp.status_code
        if resp.status_code == 200:
            break
        # Out of quota (429) or model unavailable (404): try the next model.
        if resp.status_code in (429, 404):
            continue
        # Other errors aren't model-specific — stop trying.
        break

    if resp is None or resp.status_code != 200:
        if last_status == 429:
            return _with_case(
                "Le service d'analyse d'image est très sollicité pour le "
                "moment (quota atteint). Veuillez réessayer plus tard.",
                confidence="Faible",
                risk_level="Indisponible",
                crop=crop,
                growth_stage=growth_stage,
                location=location,
            )
        return _with_case(
            "Désolé, l'analyse de l'image a échoué. Veuillez réessayer "
            "plus tard.",
            confidence="Faible",
            risk_level="Indisponible",
            crop=crop,
            growth_stage=growth_stage,
            location=location,
        )

    try:
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError, ValueError):
        return _with_case(
            "Désolé, je n'ai pas pu interpréter la réponse d'analyse. "
            "Veuillez réessayer.",
            confidence="Faible",
            risk_level="Indisponible",
            crop=crop,
            growth_stage=growth_stage,
            location=location,
        )

    if _UNCLEAR_SENTINEL in text and len(text) <= len(_UNCLEAR_SENTINEL) + 5:
        return _with_case(
            UNCLEAR_MESSAGE,
            unclear=True,
            crop=crop,
            growth_stage=growth_stage,
            location=location,
        )

    structured = _extract_json_object(text)
    if structured:
        answer = structured.get("reponse_courte") or " ".join(
            structured.get("observations", [])
        )
        answer = answer.strip()
        if "pas un diagnostic" not in answer.lower():
            answer = f"{answer}\n\n{DISCLAIMER}"
        return _with_case(
            answer,
            observations=structured.get("observations"),
            possible_causes=structured.get("problemes_possibles"),
            actions=structured.get("actions_immediates"),
            confidence=structured.get("niveau_de_confiance", "Moyen"),
            confirmation=structured.get(
                "a_confirmer_par",
                "Montrez la plante à un agent agricole pour confirmer.",
            ),
            crop=crop,
            growth_stage=growth_stage,
            location=location,
        )

    # Guarantee the non-diagnosis disclaimer is present.
    if "pas un diagnostic" not in text.lower():
        text = f"{text}\n\n{DISCLAIMER}"
    return _with_case(
        text,
        crop=crop,
        growth_stage=growth_stage,
        location=location,
    )
