"""Intent router for DakiKobo.

Decides how a question should be answered. Today there are two intents:
  - "fertilizer": a fertilizer/fumure question about a supported crop -> handled
    by the deterministic, source-grounded fertilizer tool.
  - "rag": everything else -> handled by the RAG chain (default).

Keeping this in one place makes the dispatch testable and easy to extend later
(e.g. a "disease" intent for image screening) without touching the routes.
"""

from core.fertilizer import is_fertilizer_query, get_fertilizer_advice

INTENT_FERTILIZER = "fertilizer"
INTENT_RAG = "rag"


def classify(query: str) -> str:
    """Return the intent for a query.

    Only routes to the fertilizer tool when the question is about fertilizer AND
    names a supported crop (so generic "quelle dose ?" still falls back to RAG).
    """
    if is_fertilizer_query(query) and get_fertilizer_advice(query) is not None:
        return INTENT_FERTILIZER
    return INTENT_RAG
