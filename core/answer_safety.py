"""Guardrails for every model-generated sentence DakiKobo shows a farmer.

This module owns three related responsibilities.

1. **Deployment identity.** ``safety_policy_revision()`` is a stable string that
   changes whenever the safety policy or a model prompt changes, even when no
   document in the corpus changed. Answer caches (server and browser) mix it
   into their keys so a code-only safety deployment cannot keep serving answers
   produced under the previous rules.

2. **Vision payload validation.** Gemini returns free-form JSON. Any field may
   be missing, wrongly typed, or nested. ``normalize_vision_payload`` coerces it
   to a fully typed shape without raising, and caps the reported confidence at
   ``Moyen`` so a photo screening can never claim ``Fort``.

3. **Unsafe-advice redaction.** A model must not name a pesticide product, state
   a chemical dose, or assert a definitive diagnosis. Offending sentences are
   removed and replaced by a French notice telling the farmer to confirm with an
   extension agent. Deterministic guidance in ``core.fertilizer`` remains the
   only place allowed to state input figures, and it currently withholds them
   pending agronomist review.

The bias is deliberately conservative: when a sentence is ambiguous it is
dropped. Losing a hedged sentence is cheaper than telling a smallholder to spray
an invented product at an invented rate.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

# ---------------------------------------------------------------------------
# Deployment identity for the safety policy
# ---------------------------------------------------------------------------

# Bump this when the safety rules change in a way operators should see in logs
# and headers. The digest below additionally covers accidental prompt edits.
SAFETY_POLICY_VERSION = "safety-2026-09-09"

# Source files whose contents define what a farmer may be told: this policy, the
# vision prompt/guarantees, the deterministic dose gate, and the RAG prompt.
_POLICY_SOURCE_FILES = (
    "answer_safety.py",
    "disease.py",
    "fertilizer.py",
    "llm_chain.py",
)


@lru_cache(maxsize=1)
def safety_policy_revision() -> str:
    """Return ``<version>.<digest>`` identifying the deployed safety policy.

    The digest covers the declared version plus the bytes of every prompt/policy
    source file, so editing a prompt or a guardrail invalidates cached answers
    even though the document corpus is unchanged.
    """
    digest = hashlib.sha256(SAFETY_POLICY_VERSION.encode("utf-8"))
    core_dir = Path(__file__).resolve().parent
    for name in _POLICY_SOURCE_FILES:
        digest.update(name.encode("utf-8"))
        try:
            digest.update((core_dir / name).read_bytes())
        except OSError:
            # Frozen/partial deployment: the declared version still separates
            # deliberate policy changes from one another.
            digest.update(b"<unavailable>")
    return f"{SAFETY_POLICY_VERSION}.{digest.hexdigest()[:12]}"


# ---------------------------------------------------------------------------
# Farmer-facing French notices
# ---------------------------------------------------------------------------

REDACTION_NOTICE = (
    "⚠️ Une partie de cette réponse a été retirée : DakiKobo ne donne pas de nom "
    "de produit de traitement, ni de dose chimique, ni de diagnostic ferme. "
    "Demandez le produit et la dose exacte à votre agent agricole avant toute "
    "application."
)

BLOCKED_ADVICE_ANSWER = (
    "Je ne peux pas donner ce conseil en toute sécurité. Je ne nomme pas de "
    "produit de traitement, je ne donne pas de dose chimique et je ne pose pas "
    "de diagnostic. Décrivez ce que vous observez au champ (culture, stade, "
    "feuilles, tiges, épis) à votre agent agricole ou au service de "
    "vulgarisation : ils peuvent confirmer sur place et indiquer le traitement "
    "adapté à votre parcelle."
)

# ---------------------------------------------------------------------------
# Vision confidence clamp
# ---------------------------------------------------------------------------

#: A photo screening is an aid, never a diagnosis, so ``Fort`` is unreachable.
VISION_CONFIDENCE_CEILING = "Moyen"
VISION_CONFIDENCE_FLOOR = "Faible"
VISION_CONFIDENCE_LEVELS = (VISION_CONFIDENCE_FLOOR, VISION_CONFIDENCE_CEILING)

_MEDIUM_CONFIDENCE_WORDS = frozenset({"moyen", "moyenne", "medium", "moderee", "moderate"})
# Recognised "high" labels are capped down to the ceiling rather than trusted.
_HIGH_CONFIDENCE_WORDS = frozenset(
    {
        "fort",
        "forte",
        "eleve",
        "elevee",
        "haute",
        "haut",
        "high",
        "strong",
        "certain",
        "certaine",
        "sure",
        "totale",
    }
)


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _fold(text: str) -> str:
    """Accent-insensitive, case-insensitive comparison form."""
    return _strip_accents(str(text or "")).casefold()


def clamp_vision_confidence(value) -> str:
    """Coerce a model-reported confidence into ``Faible`` or ``Moyen``.

    ``Fort`` (and every synonym) is capped at ``Moyen``. Anything unrecognised,
    missing, or non-textual degrades to ``Faible`` rather than being trusted.
    """
    folded = _fold(normalize_scalar(value)).strip(" .:;!?-_\t")
    if not folded:
        return VISION_CONFIDENCE_FLOOR
    first = folded.split()[0]
    if first in _MEDIUM_CONFIDENCE_WORDS or first in _HIGH_CONFIDENCE_WORDS:
        return VISION_CONFIDENCE_CEILING
    return VISION_CONFIDENCE_FLOOR


def clamp_case_confidence(case: dict | None) -> dict | None:
    """Return ``case`` with its confidence clamped to the vision ceiling."""
    if not isinstance(case, dict):
        return case
    clamped = dict(case)
    clamped["confidence"] = clamp_vision_confidence(clamped.get("confidence"))
    return clamped


# ---------------------------------------------------------------------------
# JSON type normalisation
# ---------------------------------------------------------------------------

def normalize_scalar(value) -> str:
    """Coerce any JSON value to clean text, never raising.

    Booleans carry no farmer-facing meaning and become empty. Lists and objects
    are flattened so a model that returns ``{"reponse_courte": ["a", "b"]}``
    still produces usable French instead of a ``TypeError``.
    """
    if value is None or isinstance(value, bool):
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        value = list(value.values())
    if isinstance(value, (list, tuple, set)):
        parts = [normalize_scalar(item) for item in value]
        return " ".join(part for part in parts if part).strip()
    return ""


def normalize_string_list(value, *, limit: int = 6) -> list[str]:
    """Coerce any JSON value to a de-duplicated list of clean strings."""
    if value is None or isinstance(value, bool):
        return []
    if isinstance(value, dict):
        candidates = list(value.values())
    elif isinstance(value, (list, tuple, set)):
        candidates = list(value)
    else:
        candidates = [value]

    items: list[str] = []
    for candidate in candidates:
        text = normalize_scalar(candidate)
        if text and text not in items:
            items.append(text)
    return items[:limit]


#: Keys the vision prompt asks for, with the type each one is coerced to.
VISION_LIST_FIELDS = ("observations", "problemes_possibles", "actions_immediates")
VISION_TEXT_FIELDS = ("a_confirmer_par", "reponse_courte")


def normalize_vision_payload(payload) -> dict | None:
    """Validate and normalise a parsed Gemini Vision JSON object.

    Returns a payload whose list fields are lists of strings, whose text fields
    are strings, and whose confidence is ``Faible`` or ``Moyen``. Returns
    ``None`` when the model did not return a JSON *object* (for example a bare
    list or string), so the caller can fall back to the plain-text path instead
    of calling ``.get`` on a non-mapping.
    """
    if not isinstance(payload, dict):
        return None

    normalized: dict[str, object] = {}
    for key in VISION_LIST_FIELDS:
        normalized[key] = normalize_string_list(
            payload.get(key),
            limit=3 if key == "actions_immediates" else 6,
        )
    for key in VISION_TEXT_FIELDS:
        normalized[key] = normalize_scalar(payload.get(key))
    normalized["niveau_de_confiance"] = clamp_vision_confidence(
        payload.get("niveau_de_confiance")
    )
    return normalized


# ---------------------------------------------------------------------------
# Unsafe content detection
# ---------------------------------------------------------------------------

PESTICIDE_PRODUCT = "pesticide_product"
CHEMICAL_DOSE = "chemical_dose"
DEFINITIVE_DIAGNOSIS = "definitive_diagnosis"

# Active ingredients and distinctive trade names quoted in West African advice.
# Matched on normalized token/phrase boundaries, never as bare substrings: a
# substring match flagged "décision" (folds to "decision", which contains the
# trade name "decis"). See ``_build_pesticide_pattern``.
_PESTICIDE_TERMS = (
    "mancozeb",
    "metalaxyl",
    "chlorothalonil",
    "difenoconazole",
    "tebuconazole",
    "azoxystrobine",
    "propiconazole",
    "hexaconazole",
    "carbendazime",
    "thiophanate",
    "chlorpyrifos",
    "chlorpyriphos",
    "imidaclopride",
    "imidacloprid",
    "acetamipride",
    "thiamethoxame",
    "clothianidine",
    "cyhalothrine",
    "deltamethrine",
    "cypermethrine",
    "permethrine",
    "bifenthrine",
    "esfenvalerate",
    "indoxacarbe",
    "emamectine",
    "abamectine",
    "spinosad",
    "spinetoram",
    "chlorantraniliprole",
    "flubendiamide",
    "profenofos",
    "dimethoate",
    "malathion",
    "dichlorvos",
    "monocrotophos",
    "triazophos",
    "methomyl",
    "oxamyl",
    "carbofuran",
    "carbaryl",
    "aldicarbe",
    "endosulfan",
    "fipronil",
    "glyphosate",
    "glufosinate",
    "atrazine",
    "paraquat",
    "pendimethaline",
    "nicosulfuron",
    "oxadiazon",
    "phosphure d'aluminium",
    "phosphure de zinc",
    "bromure de methyle",
    "bouillie bordelaise",
    # Distinctive regional trade names.
    "decis",
    "karate",
    "sherpa",
    "furadan",
    "gramoxone",
    "roundup",
    "ridomil",
    "topsin",
    "thionex",
    "lambdax",
    "cydim",
    "callifan",
    "actellic",
    "sofagrain",
    "phostoxin",
)

def _build_pesticide_pattern(terms) -> "re.Pattern[str]":
    """Compile the pesticide lexicon as whole-token / whole-phrase matches.

    Terms are matched against the accent-stripped, lower-cased text but only at
    token boundaries, where a boundary is the start/end of the string or any
    character that is not a letter, digit, or apostrophe. This way "decis"
    matches the standalone trade name and "phosphure d'aluminium" matches as a
    phrase, while "decision" (which merely contains "decis") does not.
    """
    boundary_left = r"(?:(?<=^)|(?<=[^a-z0-9']))"
    # A short, closed set of French inflection endings may follow a term before
    # the boundary, so "mancozeb" matches "mancozèbe" and a plural trade name
    # matches, without letting "decis" reach into "decision" ("ion" is not an
    # allowed ending).
    inflection = r"(?:e|es|s)?"
    boundary_right = r"(?=$|[^a-z0-9'])"
    alternatives = "|".join(
        re.escape(_fold(term)).replace(r"\ ", r"\s+") for term in terms
    )
    return re.compile(f"{boundary_left}(?:{alternatives}){inflection}{boundary_right}")


_PESTICIDE_PATTERN = _build_pesticide_pattern(_PESTICIDE_TERMS)


# Recommending an unnamed product class is unsafe advice too.
_PRODUCT_CLASS_RECOMMENDATION = re.compile(
    r"\b(?:appliqu\w*|pulveris\w*|traite\w*|vaporis\w*|asperg\w*|utilis\w*|"
    r"achet\w*|melang\w*|arros\w*)\b[^.!?]{0,80}?"
    r"\b(?:insecticide|fongicide|herbicide|pesticide|acaricide|nematicide|"
    r"raticide|produit chimique|produit phytosanitaire|matiere active)\b"
)

# A quantity that could be read as an application rate.
_QUANTITY = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*"
    r"(?:kg|kilogrammes?|kilos?|g|grammes?|mg|l|litres?|ml|cl|cc|"
    r"sachets?|bouchons?|cuilleres?|capsules?|doses?)\b"
)
# A fertilizer formulation such as 14-23-14 is itself a dose statement.
_NPK_FORMULA = re.compile(r"\b\d{1,2}\s*-\s*\d{1,2}\s*-\s*\d{1,2}\b")
# Chemical context that turns a bare quantity into an application rate.
_CHEMICAL_CONTEXT = re.compile(
    r"\b(?:engrais|npk|npkb|uree|dap|tsp|kcl|potasse|phosphate|ammonitrate|"
    r"sulfate|nitrate|azote|cuivre|soufre|fumure|microdose|micro-dose|"
    r"insecticide|fongicide|herbicide|pesticide|acaricide|nematicide|"
    r"produit|traitement|bouillie|matiere active|dose|dosage|solution|"
    r"pulverisation|semence traitee)\b"
)

# Diagnosis patterns run against accent-preserving lower case. Stripping accents
# would merge the preposition "à" into the verb "a" and wrongly flag the
# mandatory disclaimer ("montrez la plante à votre agent agricole").
_DISEASE_TERMS = (
    r"(?:rouille|mildiou|charbon|anthracnose|fusariose|fl[eé]trissure|virose|"
    r"mosa[iï]que|bact[eé]riose|n[eé]matodes?|chenilles?|pucerons?|criquets?|"
    r"cochenilles?|thrips|acariens?|striga|carences?|maladie|champignon|"
    r"insectes?|ravageurs?|pourriture|o[iï]dium|septoriose|cercosporiose|"
    r"l[eé]gionnaire|foreur|borer|mineuse|charan[cç]ons?|bruches?)"
)

# Marker that a sentence is actually about a disease, pest, symptom, or plant
# damage. Generic certainty ("il s'agit de…", "c'est certainement…") is only a
# diagnosis when it appears alongside this context, so ordinary confident
# statements about programmes, techniques, or timing are left untouched.
_DIAGNOSIS_CONTEXT = re.compile(
    _DISEASE_TERMS
    + r"|\b(?:sympt[oô]mes?|tach(?:e|es)|l[eé]sions?|jaunissement|"
    r"fl[eé]trit|attaqu[eé]e?s?|infest\w*|infect\w*|contamin\w*|"
    r"d[eé]g[aâ]ts?|pourri\w*|moisiss\w*|d[eé]p[eé]riss\w*)\b"
)

# Sentence-level assertions that state a firm diagnosis when disease context is
# present. Each is applied only after ``_DIAGNOSIS_CONTEXT`` matches the
# sentence, so it never fires on a confident non-agronomic statement.
_DIAGNOSIS_ASSERTIONS = (
    # The prompt mandates the hedged "il pourrait s'agir de"; the indicative
    # "il s'agit de" is an assertion. "il s'agit peut-être" stays hedged.
    re.compile(r"\bil s'agit\b(?!\s+(?:peut-[eê]tre|probablement|sans doute\b))"),
    re.compile(r"\bc'est\s+(?:bien|clairement|certainement|s[uû]rement)?\s*"
               r"(?:un|une|le|la|l'|du|de la|des)?\s*" + _DISEASE_TERMS),
    # "La cause est la rouille", "le problème est une carence".
    re.compile(r"\b(?:la cause|le probl[eè]me|le souci|l'origine)\s+"
               r"(?:en\s+)?est\b"),
    # "Ces signes confirment une rouille", "cela confirme le mildiou".
    re.compile(r"\bconfirm(?:e|ent|ons)\b"),
    re.compile(r"\bsignes?\s+(?:confirm\w+|indiquent|montrent|r[eé]v[eè]lent)\b"),
    # Certainty adverbs — only counted when the sentence has disease context.
    re.compile(
        r"\b(?:certainement|assur[eé]ment|indubitablement|à coup s[uû]r|"
        r"avec certitude|sans aucun doute)\b"
    ),
    re.compile(r"\b100\s*%\s*(?:s[uû]r|certain)\b"),
    re.compile(r"\b(?:votre|la|cette)\s+plante\s+(?:a\s|souffre|est atteinte)"),
)

# Assertions that are firm diagnoses on their own, regardless of extra context
# (they already name the clinical act or a confirmed disease).
_DIAGNOSIS_UNCONDITIONAL = (
    re.compile(r"\bdiagnostic\s*[:=]"),
    re.compile(r"\bje (?:confirme|diagnostique)\b"),
    re.compile(r"\bmaladie (?:identifi[eé]e|confirm[eé]e|certaine)\b"),
)


def _is_definitive_diagnosis(lowered: str) -> bool:
    """True when the sentence states a firm diagnosis.

    A generic certainty phrase counts only when the sentence also carries
    disease/pest/symptom/plant-damage context, so confident statements about
    programmes, techniques, or timing are not treated as diagnoses.
    """
    if any(pattern.search(lowered) for pattern in _DIAGNOSIS_UNCONDITIONAL):
        return True
    if not _DIAGNOSIS_CONTEXT.search(lowered):
        return False
    return any(pattern.search(lowered) for pattern in _DIAGNOSIS_ASSERTIONS)


def unsafe_reasons(sentence: str, *, check_diagnosis: bool = True) -> tuple[str, ...]:
    """Return the reason codes making one sentence unsafe to show a farmer."""
    text = normalize_scalar(sentence)
    if not text.strip():
        return ()
    # Active-ingredient spellings vary in accentuation, so product and dose
    # matching uses the accent-stripped form.
    folded = _fold(text)
    lowered = text.casefold()

    reasons: list[str] = []
    if _PESTICIDE_PATTERN.search(folded) or _PRODUCT_CLASS_RECOMMENDATION.search(
        folded
    ):
        reasons.append(PESTICIDE_PRODUCT)

    # A bare quantity is a dose only next to a fertilizer, product, or treatment
    # word. Requiring chemical context for every quantity — including per-plant
    # and per-pied rates — keeps legitimate irrigation ("20 litres d'eau par
    # pied"), seed ("20 kg de semences"), spacing ("80 cm"), compost ("5 kg de
    # compost par pied"), and yield ("1 200 kg/ha de rendement") quantities.
    if _NPK_FORMULA.search(folded) or (
        _QUANTITY.search(folded) and _CHEMICAL_CONTEXT.search(folded)
    ):
        reasons.append(CHEMICAL_DOSE)

    if check_diagnosis and _is_definitive_diagnosis(lowered):
        reasons.append(DEFINITIVE_DIAGNOSIS)

    return tuple(reasons)


def is_safe_sentence(sentence: str, *, check_diagnosis: bool = True) -> bool:
    """True when a sentence carries no unsafe product, dose, or diagnosis."""
    return not unsafe_reasons(sentence, check_diagnosis=check_diagnosis)


@dataclass(frozen=True)
class SafetyReview:
    """Outcome of screening one model-generated block of French text."""

    text: str
    reasons: tuple[str, ...] = ()
    blocked: bool = False

    @property
    def redacted(self) -> bool:
        """True when at least one sentence was removed."""
        return bool(self.reasons)


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])\s+")


def _line_prefix(line: str) -> str:
    match = re.match(r"^[\s•\-\*\u2022\u25cf]*", line)
    return match.group(0) if match else ""


# A quantity in one sentence and its chemical noun in a neighbour ("L'urée
# convient. Appliquez 100 kg/ha.") together form a dose. Evaluation therefore
# uses a small window of surrounding sentences, not the sentence alone.
_CONTEXT_WINDOW = 1


def _dose_context_in_window(sentences, index) -> bool:
    """True when a quantity sentence has chemical context in a nearby sentence."""
    start = max(0, index - _CONTEXT_WINDOW)
    end = min(len(sentences), index + _CONTEXT_WINDOW + 1)
    window = " ".join(sentences[start:end])
    return bool(_CHEMICAL_CONTEXT.search(_fold(window)))


def redact_unsafe_text(text, *, check_diagnosis: bool = True) -> SafetyReview:
    """Drop unsafe sentences from generated text, preserving line structure.

    ``blocked`` is True when the text had content but nothing safe survived; the
    caller must then substitute a deterministic refusal rather than show an
    empty answer.

    A bare quantity is judged against a short window of neighbouring sentences,
    so a dose split across sentences ("L'urée convient. Appliquez 100 kg/ha.")
    is still removed even though neither sentence names both parts alone.
    """
    original = normalize_scalar(text)
    if not original:
        return SafetyReview(text="", reasons=(), blocked=False)

    # Sentence positions are tracked across the whole block so the dose window
    # can look past a line break, while line structure is still rebuilt below.
    block_sentences: list[str] = []
    line_plan: list[tuple[str, list[int]]] = []  # (prefix, sentence indices)
    for line in original.splitlines():
        if not line.strip():
            line_plan.append(("", []))
            continue
        prefix = _line_prefix(line)
        body = line[len(prefix):]
        indices = []
        for sentence in _SENTENCE_SPLIT.split(body):
            if not sentence.strip():
                continue
            indices.append(len(block_sentences))
            block_sentences.append(sentence.strip())
        line_plan.append((prefix, indices))

    had_content = any(indices for _, indices in line_plan)

    reasons: list[str] = []
    kept_lines: list[str] = []
    for prefix, indices in line_plan:
        if not indices:
            kept_lines.append("")
            continue
        safe_parts = []
        for sentence_index in indices:
            sentence = block_sentences[sentence_index]
            found = list(unsafe_reasons(sentence, check_diagnosis=check_diagnosis))
            # A quantity with no in-sentence chemical word is still a dose when
            # a neighbouring sentence supplies that word.
            if (
                CHEMICAL_DOSE not in found
                and _QUANTITY.search(_fold(sentence))
                and _dose_context_in_window(block_sentences, sentence_index)
            ):
                found.append(CHEMICAL_DOSE)
            if found:
                for reason in found:
                    if reason not in reasons:
                        reasons.append(reason)
                continue
            safe_parts.append(sentence)
        if safe_parts:
            kept_lines.append(prefix + " ".join(safe_parts))

    cleaned = "\n".join(kept_lines).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    if had_content and not cleaned:
        return SafetyReview(text="", reasons=tuple(reasons), blocked=True)
    return SafetyReview(text=cleaned, reasons=tuple(reasons), blocked=False)


def filter_safe_items(items, *, check_diagnosis: bool = True) -> tuple[list[str], tuple[str, ...]]:
    """Keep only the safe entries of a normalised list field."""
    reasons: list[str] = []
    safe: list[str] = []
    for item in normalize_string_list(items, limit=12):
        found = unsafe_reasons(item, check_diagnosis=check_diagnosis)
        if found:
            for reason in found:
                if reason not in reasons:
                    reasons.append(reason)
            continue
        safe.append(item)
    return safe, tuple(reasons)


def with_redaction_notice(text: str, reasons) -> str:
    """Append the French redaction notice when something was removed."""
    if not reasons:
        return text
    body = (text or "").strip()
    if REDACTION_NOTICE in body:
        return body
    return f"{body}\n\n{REDACTION_NOTICE}".strip()


# Stems showing the confirmation line actually directs the farmer to a person
# or place that can confirm on the ground. The vision prompt asks for exactly
# this. Matched as token-initial stems (so "vulgaris" covers "vulgarisation"
# and "vulgarisateur") to tolerate French inflection.
_AGENT_DIRECTION_STEMS = (
    "agent",
    "agronome",
    "vulgaris",
    "technicien",
    "encadr",
    "cooperative",
    "conseiller",
    "expert",
    "specialiste",
    "laboratoire",
    "clinique",
)
_AGENT_DIRECTION_PATTERN = re.compile(
    r"(?:(?<=^)|(?<=[^a-z0-9']))(?:"
    + "|".join(re.escape(stem) for stem in _AGENT_DIRECTION_STEMS)
    + r")[a-z]*"
)


def safe_confirmation(value, *, fallback: str) -> str:
    """Return a trustworthy agent-confirmation line, or the deterministic fallback.

    The model's ``a_confirmer_par`` is replaced by ``fallback`` when it is
    empty, malformed (too short/long to be a real instruction), carries an
    unsafe product/dose/diagnosis, or does not actually point the farmer at a
    person or place that can confirm. The confirmation line is mandatory, so it
    must never be dropped and never smuggle unsafe content.
    """
    text = normalize_scalar(value)
    if not text:
        return fallback
    # A real instruction is a short sentence, not a word or a paragraph.
    if len(text) < 8 or len(text) > 200:
        return fallback
    if unsafe_reasons(text):
        return fallback
    if not _AGENT_DIRECTION_PATTERN.search(_fold(text)):
        return fallback
    return text
