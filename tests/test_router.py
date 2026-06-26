"""Tests for the intent router (no network / no LLM)."""

from core.router import classify, INTENT_FERTILIZER, INTENT_RAG


def test_fertilizer_with_crop_routes_to_tool():
    assert classify("dose d'engrais pour le sorgho") == INTENT_FERTILIZER
    assert classify("quelle fumure pour le maïs ?") == INTENT_FERTILIZER


def test_fertilizer_without_crop_falls_back_to_rag():
    assert classify("quelle dose d'engrais utiliser ?") == INTENT_RAG


def test_normal_question_routes_to_rag():
    assert classify("quand semer le mil ?") == INTENT_RAG
    assert classify("comment lutter contre le striga ?") == INTENT_RAG
