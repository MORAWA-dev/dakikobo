"""Smoke test for the RAG chain answering a French crop question.

This is a live test: it needs a GROQ_API_KEY (and downloads the embedding model
on first run), so it is skipped automatically when no key is configured.
"""

import os

import pytest

import config  # triggers load_dotenv() so GROQ_API_KEY is read from .env

GROQ_KEY = os.getenv("GROQ_API_KEY", "")


@pytest.mark.skipif(
    not GROQ_KEY, reason="GROQ_API_KEY not set; skipping live LLM smoke test"
)
def test_french_crop_question_returns_answer():
    # Imported lazily: instantiating ChatGroq requires the API key, so keep it
    # out of module import / collection time.
    from langchain_community.vectorstores import Chroma
    from langchain_community.embeddings.sentence_transformer import (
        SentenceTransformerEmbeddings,
    )
    from langchain_core.documents import Document
    from core.llm_chain import setup_retrieval_qa

    emb = SentenceTransformerEmbeddings(model_name=config.EMBEDDING_MODEL)
    docs = [
        Document(
            page_content=(
                "Le mil se sème au début de la saison des pluies au Sahel, "
                "généralement en juin-juillet, dès les premières pluies utiles."
            ),
            metadata={"source": "guide_mil.pdf"},
        ),
        Document(
            page_content=(
                "Le sorgho reçoit de la fumure organique et de l'urée au stade "
                "tallage pour de bons rendements."
            ),
            metadata={"source": "guide_sorgho.pdf"},
        ),
    ]
    db = Chroma.from_documents(
        docs, emb, collection_metadata={"hnsw:space": "cosine"}
    )
    chain = setup_retrieval_qa(db)

    result = chain.invoke("Quand semer le mil ?")
    answer = result["result"]
    assert isinstance(answer, str) and answer.strip(), "chain returned an empty answer"
