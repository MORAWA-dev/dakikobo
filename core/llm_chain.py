# core/llm_chain.py — LLM initialization and RetrievalQA chain setup

import re

from langchain_groq import ChatGroq
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

from config import (
    GROQ_API_KEY,
    GROQ_USER_AGENT,
    LLM_MODEL,
    LLM_MAX_TOKENS,
    LLM_MAX_RETRIES,
    LLM_REASONING_EFFORT,
    LLM_REASONING_FORMAT,
    LLM_TEMPERATURE,
    LLM_TIMEOUT_SECONDS,
    SIMILARITY_THRESHOLD,
    BOT_NAME,
)

# =================================================================
# LLM
# =================================================================

_llm = None

# Groq model families that accept `reasoning_format` / `reasoning_effort`.
# Sending these params to a non-reasoning model returns HTTP 400, so they are
# opt-in by model prefix rather than always-on.
_REASONING_MODEL_PREFIXES = ("openai/gpt-oss", "qwen/")


def _reasoning_model_kwargs(model: str) -> dict:
    """Return Groq reasoning params for reasoning-capable models only.

    DakiKobo shows answers directly to farmers, so chain-of-thought must never
    reach the UI. `reasoning_format="hidden"` keeps the response to the answer.
    """
    if not model.startswith(_REASONING_MODEL_PREFIXES):
        return {}

    kwargs = {}
    if LLM_REASONING_FORMAT:
        kwargs["reasoning_format"] = LLM_REASONING_FORMAT
    if LLM_REASONING_EFFORT:
        kwargs["reasoning_effort"] = LLM_REASONING_EFFORT
    return kwargs


def strip_reasoning(text: str) -> str:
    """Remove any chain-of-thought that leaked into a farmer-facing answer.

    `reasoning_format="hidden"` is the primary defence, but Groq has a known
    gpt-oss bug where reasoning tokens still appear in `content`. Farmers must
    never see the model thinking out loud, so strip it defensively.

    Only reasoning wrappers are removed. If stripping would empty the answer,
    the original text is returned so a real answer is never silently lost.
    """
    if not text:
        return text

    cleaned = text
    # Tag-delimited reasoning, including an unclosed trailing block.
    for tag in ("think", "thinking", "reasoning", "analysis"):
        cleaned = re.sub(
            rf"<{tag}>.*?</{tag}>", "", cleaned, flags=re.DOTALL | re.IGNORECASE
        )
        cleaned = re.sub(
            rf"<{tag}>.*\Z", "", cleaned, flags=re.DOTALL | re.IGNORECASE
        )

    # Harmony-style channel markers used by gpt-oss.
    cleaned = re.sub(
        r"<\|(?:start|end|channel|message|return)\|>", "", cleaned, flags=re.IGNORECASE
    )
    cleaned = re.sub(
        r"^\s*(?:analysis|commentary)\b.*?(?=\bfinal\b)", "", cleaned,
        flags=re.DOTALL | re.IGNORECASE,
    )
    cleaned = re.sub(r"^\s*final\s*[:>-]?\s*", "", cleaned, flags=re.IGNORECASE)

    cleaned = cleaned.strip()
    return cleaned or text.strip()


def get_llm():
    """Create the Groq client only when a RAG answer is requested."""
    global _llm
    if _llm is None:
        if not GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY is not configured.")
        _llm = ChatGroq(
            model=LLM_MODEL,
            max_tokens=LLM_MAX_TOKENS,
            temperature=LLM_TEMPERATURE,
            timeout=LLM_TIMEOUT_SECONDS,
            max_retries=LLM_MAX_RETRIES,
            groq_api_key=GROQ_API_KEY,
            default_headers={"User-Agent": GROQ_USER_AGENT},
            # Passed through langchain-groq's model_kwargs to the Groq SDK.
            model_kwargs=_reasoning_model_kwargs(LLM_MODEL),
        )
    return _llm

# =================================================================
# RAG CHAIN
# =================================================================

_PROMPT_TEMPLATE = f"""
Your name is {BOT_NAME}, a specialized agricultural extension expert for smallholder farmers in **Burkina Faso**.
- **Focus:** Answer using knowledge relevant to the **Sahel** and **Sudanian Savanna** zones.
- **Crops:** Prioritize **Sorghum, Millet, Maize, Cotton, Niébé (Cowpea), Groundnuts, Soybean (soja)**. Also help for other local field crops when the CONTEXT allows.
- **Language:** ALWAYS reply in French (français), whatever the language of the question. Use simple, clear French that a farmer can understand, and address the user as "vous".
- **Style:** Keep answers simple, practical, and under 100 words. Short sentences only. Be concrete (sol, semis, pluie, préparation) when CONTEXT supports it.
- **Structure:** Prefer: (1) one direct answer sentence on the asked topic, (2) 1-3 concrete actions, (3) one caution if needed. No rigid markdown headings. Never paste market lists, place-name lists, or raw document tables.
- **Topic priority (critical):** Answer the **crop and place named in the QUESTION**. If a "parcelle" form crop differs (e.g. form=sorgho but question=soja), ignore the form crop for the advice and answer the question crop. Do not talk about watering sorghum when the user asked about soybean sowing.
- **Follow-ups:** If the question includes a short precision (e.g. "ok à Ouagadougou") after a prior topic, keep the prior crop/topic and only update the place or detail.
- **Safety:** Never invent exact fertilizer doses, pesticide product names, or precise calendar dates. If those details are missing, give safe general practice and say to confirm doses with an agent agricole.
- **Uncertainty (rare):** Use "Je ne peux pas confirmer." **only** for diagnosis, pesticide choice, exact dose, or when CONTEXT is empty/irrelevant. For partial CONTEXT, still give useful general field advice and end with a short confirmation line. Do **not** refuse just because the form crop differs or location is approximate.
- **Constraint:** Ground the answer in the provided CONTEXT. If CONTEXT has nothing useful for the question topic, reply exactly: "Je ne sais pas encore. Cette information n'est pas disponible dans la base de données de {BOT_NAME} pour le Burkina Faso."

CONTEXT: {{context}}
QUESTION: {{question}}"""

PROMPT = PromptTemplate(
    template=_PROMPT_TEMPLATE,
    input_variables=["context", "question"],
)


def setup_retrieval_qa(db):
    """Build and return a RetrievalQA chain from an initialized vector store."""
    if db is None:
        raise RuntimeError("Vector store is not initialized.")

    retriever = db.as_retriever(
        search_type="similarity_score_threshold",
        # k=6 gives field-practice questions a better chance to surface
        # extension manuals (IITA/ProSol) over livelihood profiles.
        search_kwargs={"score_threshold": SIMILARITY_THRESHOLD, "k": 6},
    )
    chain = RetrievalQA.from_chain_type(
        llm=get_llm(),
        chain_type="stuff",
        retriever=retriever,
        input_key="query",
        return_source_documents=True,
        chain_type_kwargs={"prompt": PROMPT},
        verbose=True,
    )
    return chain
