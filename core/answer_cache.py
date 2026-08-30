"""Stable, corpus-aware answer caching for repeat agricultural questions."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

from config import (
    ANSWER_CACHE_TTL_SECONDS,
    LLM_MODEL,
    QUESTION_HASH_SALT,
    STATE_DB_PATH,
)
from core.cache import TTLCache
from core.retrieval import get_active_manifest_hash


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_question(question: str) -> str:
    """Collapse whitespace and casefold without destroying French accents."""
    return " ".join((question or "").casefold().split())


def build_answer_cache_key(
    question: str,
    *,
    crop_id: str = "",
    growth_stage: str = "",
    place_id: str = "",
    simple_french: bool = False,
    llm_model: str = LLM_MODEL,
    manifest_hash_value: str | None = None,
) -> str:
    """Build the locked Phase 3 key over question, context, model, and corpus."""
    active_manifest = (
        get_active_manifest_hash()
        if manifest_hash_value is None
        else manifest_hash_value
    )
    material = "|".join(
        (
            normalize_question(question),
            (crop_id or "").strip().casefold(),
            (growth_stage or "").strip().casefold(),
            (place_id or "").strip().casefold(),
            "true" if simple_french else "false",
            (llm_model or "").strip(),
            active_manifest or "",
        )
    )
    return sha256(material.encode("utf-8")).hexdigest()


def question_hash(question: str, *, salt: str = QUESTION_HASH_SALT) -> str:
    """Return the privacy-safe salted hash reserved for the Phase 4 ledger."""
    return sha256(f"{salt}|{question or ''}".encode("utf-8")).hexdigest()


class AnswerCache:
    """Typed facade over the shared SQLite TTL cache."""

    def __init__(
        self,
        ttl_seconds: int = ANSWER_CACHE_TTL_SECONDS,
        *,
        db_path: str = STATE_DB_PATH,
    ):
        self._cache = TTLCache(
            "answers",
            ttl_seconds,
            db_path=db_path,
        )

    def get(self, key: str) -> dict | None:
        value = self._cache.get(key)
        if value is None:
            return None
        required = {
            "answer",
            "case",
            "sources",
            "confidence",
            "retrieved_chunk_ids",
            "cached_at",
        }
        return value if required.issubset(value) else None

    def set(
        self,
        key: str,
        *,
        answer: str,
        case: dict | None,
        sources: list[dict],
        confidence: str,
        retrieved_chunk_ids: list[str],
    ) -> dict[str, Any]:
        value = {
            "answer": answer,
            "case": case,
            "sources": sources,
            "confidence": confidence,
            "retrieved_chunk_ids": list(retrieved_chunk_ids),
            "cached_at": _utc_now_iso(),
        }
        self._cache.set(key, value)
        return value

    def purge_expired(self) -> int:
        return self._cache.purge_expired()

    def clear(self) -> int:
        return self._cache.clear()
