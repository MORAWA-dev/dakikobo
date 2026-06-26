"""Leaf disease screening via Gemini Vision (REST API, no SDK dependency).

This is a *screening aid*, not a diagnosis. The prompt forces the model to:
  - refuse politely when the photo is not a clear plant/leaf image, and
  - stay hedged ("il pourrait s'agir de…") for real photos.
The code also guarantees the "ceci n'est pas un diagnostic" disclaimer is present.
"""

import base64

import requests

from config import GEMINI_API_KEY, GEMINI_MODEL

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
    "2. Sinon, fais un dépistage PRUDENT, en français simple (vouvoiement), "
    "sous 100 mots:\n"
    "   - Décris en une phrase ce que tu observes sur la feuille.\n"
    "   - Indique le(s) problème(s) POSSIBLE(s) (maladie, carence ou ravageur) "
    "avec prudence, par exemple « il pourrait s'agir de… ».\n"
    "   - Donne 1 à 2 conseils pratiques simples.\n"
    "   Ne donne jamais de certitude et n'invente pas de produit chimique précis."
)


def is_configured() -> bool:
    """True if a Gemini API key is available."""
    return bool(GEMINI_API_KEY)


def screen_leaf_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    """Screen a leaf photo and return {"answer": str}.

    Always returns a friendly French message (never raises): handles missing key,
    network errors, rate limits (429) and unusable photos gracefully.
    """
    if not GEMINI_API_KEY:
        return {
            "answer": "La fonction d'analyse d'image n'est pas configurée "
            "(clé GEMINI_API_KEY manquante)."
        }

    b64 = base64.b64encode(image_bytes).decode("utf-8")
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": _PROMPT},
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
            return {
                "answer": "Désolé, je n'ai pas pu contacter le service d'analyse "
                "d'image. Vérifiez votre connexion et réessayez."
            }
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
            return {
                "answer": "Le service d'analyse d'image est très sollicité pour le "
                "moment (quota atteint). Veuillez réessayer plus tard."
            }
        return {
            "answer": "Désolé, l'analyse de l'image a échoué. Veuillez réessayer "
            "plus tard."
        }

    try:
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError, ValueError):
        return {
            "answer": "Désolé, je n'ai pas pu interpréter la réponse d'analyse. "
            "Veuillez réessayer."
        }

    if _UNCLEAR_SENTINEL in text and len(text) <= len(_UNCLEAR_SENTINEL) + 5:
        return {"answer": UNCLEAR_MESSAGE}

    # Guarantee the non-diagnosis disclaimer is present.
    if "pas un diagnostic" not in text.lower():
        text = f"{text}\n\n{DISCLAIMER}"
    return {"answer": text}
