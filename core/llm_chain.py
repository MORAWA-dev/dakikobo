# core/llm_chain.py — LLM initialization and RetrievalQA chain setup

from langchain_groq import ChatGroq
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

from config import (
    GROQ_API_KEY,
    LLM_MODEL,
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
    SIMILARITY_THRESHOLD,
    BOT_NAME,
)

# =================================================================
# LLM
# =================================================================

llm = ChatGroq(
    model=LLM_MODEL,
    max_tokens=LLM_MAX_TOKENS,
    temperature=LLM_TEMPERATURE,
    groq_api_key=GROQ_API_KEY,
)

# =================================================================
# RAG CHAIN
# =================================================================

_PROMPT_TEMPLATE = f"""
Your name is {BOT_NAME}, a specialized agricultural extension expert for smallholder farmers in **Burkina Faso**.
- **Focus:** Answer using knowledge relevant to the **Sahel** and **Sudanian Savanna** zones.
- **Crops:** Prioritize advice for **Sorghum, Millet, Maize, Cotton, Niébé (Cowpea), and Groundnuts**.
- **Language/Style:** Keep answers simple, practical, and under 100 words. Address the user directly as a farmer.
- **Constraint:** Use the provided CONTEXT from local Burkinabé sources to ground your answer. If the context does not contain the answer, respond with 'Don't know. Information is not yet available in the {BOT_NAME} database for Burkina Faso.'

CONTEXT: {{context}}
QUESTION: {{question}}"""

PROMPT = PromptTemplate(
    template=_PROMPT_TEMPLATE,
    input_variables=["context", "question"],
)


def setup_retrieval_qa(db):
    """Build and return a RetrievalQA chain from an initialized vector store."""
    retriever = db.as_retriever(similarity_score_threshold=SIMILARITY_THRESHOLD)
    chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        input_key="query",
        return_source_documents=True,
        chain_type_kwargs={"prompt": PROMPT},
        verbose=True,
    )
    return chain
