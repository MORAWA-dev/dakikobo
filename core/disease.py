"""Leaf disease screening via Gemini Vision (REST API, no SDK dependency).

This is a *screening aid*, not a diagnosis. The prompt forces the model to:
  - refuse politely when the photo is not a clear plant/leaf image, and
  - stay hedged ("il pourrait s'agir de…") for real photos.

Prompt rules alone are not a safety control, so the code enforces the contract:
every payload is type-validated (``core.answer_safety``), the reported
confidence is capped at ``Moyen``, pesticide names / chemical doses / definitive
diagnoses are removed, and the "ceci n'est pas un diagnostic" disclaimer plus the
agent-confirmation line are always present.

Each result also carries a ``service_status`` so the HTTP layer can answer with a
truthful status code instead of dressing an upstream failure as a 200.
"""

import base64
import json
import re

import requests

from config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_TIMEOUT_SECONDS
from core.answer_safety import (
    BLOCKED_ADVICE_ANSWER,
    clamp_vision_confidence,
    filter_safe_items,
    normalize_scalar,
    normalize_vision_payload,
    redact_unsafe_text,
    safe_confirmation,
    with_redaction_notice,
)
from core.case import build_disease_case

# Screening outcome, mapped to an HTTP status by the route.
STATUS_OK = "ok"
STATUS_NOT_CONFIGURED = "not_configured"
STATUS_UNREACHABLE = "unreachable"
STATUS_RATE_LIMITED = "rate_limited"
STATUS_UPSTREAM_ERROR = "upstream_error"
STATUS_UNREADABLE_RESPONSE = "unreadable_response"

#: Statuses that represent a genuine service failure rather than a screening.
FAILURE_STATUSES = frozenset(
    {
        STATUS_NOT_CONFIGURED,
        STATUS_UNREACHABLE,
        STATUS_RATE_LIMITED,
        STATUS_UPSTREAM_ERROR,
        STATUS_UNREADABLE_RESPONSE,
    }
)

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

# Used when the model omits `a_confirmer_par`: agent confirmation is mandatory.
CONFIRMATION_FALLBACK = "Montrez la plante à un agent agricole pour confirmer."

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


def _with_case(answer: str, *, service_status: str = STATUS_OK, **case_kwargs) -> dict:
    """Build the screening result, capping confidence at the vision ceiling."""
    case_kwargs["confidence"] = clamp_vision_confidence(
        case_kwargs.get("confidence", "Moyen")
    )
    return {
        "answer": answer,
        "service_status": service_status,
        "case": build_disease_case(
            answer=answer,
            disclaimer=DISCLAIMER,
            **case_kwargs,
        ),
    }


def _safe_screening_answer(text: str, *, block_context: str = "") -> str:
    """Strip unsafe model claims and guarantee the mandatory French messages.

    A screening answer may not name a treatment product, state a chemical dose,
    or assert a diagnosis. When nothing safe survives, the deterministic refusal
    is used instead of an empty answer. The non-diagnosis disclaimer and the
    agent-confirmation sentence are appended in both cases.
    """
    review = redact_unsafe_text(
        text,
        check_diagnosis=True,
        block_context=block_context,
    )
    body = BLOCKED_ADVICE_ANSWER if review.blocked else review.text
    body = with_redaction_notice(body, review.reasons)
    if not body.strip():
        body = BLOCKED_ADVICE_ANSWER
    if "pas un diagnostic" not in body.lower():
        body = f"{body}\n\n{DISCLAIMER}"
    return body.strip()


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
            service_status=STATUS_NOT_CONFIGURED,
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
                timeout=GEMINI_TIMEOUT_SECONDS,
            )
        except requests.RequestException:
            return _with_case(
                "Désolé, je n'ai pas pu contacter le service d'analyse "
                "d'image. Vérifiez votre connexion et réessayez.",
                service_status=STATUS_UNREACHABLE,
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
                service_status=STATUS_RATE_LIMITED,
                confidence="Faible",
                risk_level="Indisponible",
                crop=crop,
                growth_stage=growth_stage,
                location=location,
            )
        return _with_case(
            "Désolé, l'analyse de l'image a échoué. Veuillez réessayer "
            "plus tard.",
            service_status=STATUS_UPSTREAM_ERROR,
            confidence="Faible",
            risk_level="Indisponible",
            crop=crop,
            growth_stage=growth_stage,
            location=location,
        )

    try:
        payload = resp.json()
        text = normalize_scalar(
            payload["candidates"][0]["content"]["parts"][0]["text"]
        )
    except (AttributeError, KeyError, IndexError, TypeError, ValueError):
        text = ""
    if not text:
        return _with_case(
            "Désolé, je n'ai pas pu interpréter la réponse d'analyse. "
            "Veuillez réessayer.",
            service_status=STATUS_UNREADABLE_RESPONSE,
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

    # A valid JSON *object* is required. A bare list, string, or number parses
    # successfully but is not a screening payload, so it falls through to the
    # plain-text path instead of being indexed like a mapping.
    structured = normalize_vision_payload(_extract_json_object(text))
    if structured is not None:
        # An object with no usable field yields the deterministic safe refusal
        # rather than an empty answer or a dump of the raw JSON.
        structured_context = " ".join(
            [
                *structured["observations"],
                *structured["problemes_possibles"],
                *structured["actions_immediates"],
                structured["a_confirmer_par"],
                structured["reponse_courte"],
            ]
        )
        raw_answer = structured["reponse_courte"] or " ".join(
            structured["observations"]
        )
        observations, obs_reasons = filter_safe_items(
            structured["observations"], block_context=structured_context
        )
        causes, cause_reasons = filter_safe_items(
            structured["problemes_possibles"], block_context=structured_context
        )
        actions, action_reasons = filter_safe_items(
            structured["actions_immediates"], block_context=structured_context
        )
        answer = _safe_screening_answer(
            raw_answer, block_context=structured_context
        )
        # A dropped list entry is also a redaction the farmer should be told about.
        answer = with_redaction_notice(
            answer, obs_reasons + cause_reasons + action_reasons
        )
        # The confirmation line is mandatory. Replace it with the deterministic
        # fallback if the model made it unsafe, malformed, empty, or if it does
        # not actually send the farmer to an agent who can confirm.
        confirmation = safe_confirmation(
            structured["a_confirmer_par"],
            fallback=CONFIRMATION_FALLBACK,
            block_context=structured_context,
        )
        return _with_case(
            answer,
            observations=observations,
            possible_causes=causes,
            actions=actions,
            # Never above the vision ceiling, whatever the model reported.
            confidence=structured["niveau_de_confiance"],
            confirmation=confirmation,
            crop=crop,
            growth_stage=growth_stage,
            location=location,
        )

    # Plain-text screening: redact unsafe claims, then guarantee the mandatory
    # non-diagnosis disclaimer.
    return _with_case(
        _safe_screening_answer(text),
        confidence="Faible",
        crop=crop,
        growth_stage=growth_stage,
        location=location,
    )
