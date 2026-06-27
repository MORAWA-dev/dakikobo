# core/llm_chain.py — LLM initialization and RetrievalQA chain setup

from langchain_groq import ChatGroq
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

from config import (
    GROQ_API_KEY,
    GROQ_USER_AGENT,
    LLM_MODEL,
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
    SIMILARITY_THRESHOLD,
    BOT_NAME,
)

# =================================================================
# LLM
# =================================================================

_llm = None


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
            groq_api_key=GROQ_API_KEY,
            default_headers={"User-Agent": GROQ_USER_AGENT},
        )
    return _llm

# =================================================================
# RAG CHAIN
# =================================================================

_PROMPT_TEMPLATE = f"""
Your name is {BOT_NAME}, a specialized agricultural extension expert for smallholder farmers in **Burkina Faso**.
- **Focus:** Answer using knowledge relevant to the **Sahel** and **Sudanian Savanna** zones.
- **Crops:** Prioritize advice for **Sorghum, Millet, Maize, Cotton, Niébé (Cowpea), and Groundnuts**.
- **Language:** ALWAYS reply in French (français), whatever the language of the question. Use simple, clear French that a farmer can understand, and address the user as "vous".
- **Style:** Keep answers simple, practical, and under 100 words.
- **Constraint:** Use the provided CONTEXT from local Burkinabé sources to ground your answer. If the context does not contain the answer, reply in French with exactly: "Je ne sais pas encore. Cette information n'est pas disponible dans la base de données de {BOT_NAME} pour le Burkina Faso."

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
        search_kwargs={"score_threshold": SIMILARITY_THRESHOLD, "k": 4},
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
