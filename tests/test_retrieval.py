"""Citation policy tests for core.retrieval (Phase 2).

These exercise the public seam without a Flask client or a live vector store.
score_lookup is query-less and closes over an already-computed scored list.
"""

from types import SimpleNamespace

from core.retrieval import (
    GroundedAnswer,
    SourceCard,
    _is_field_practice_query,
    _is_weak_source_title,
    _source_rank_score,
    chunk_id,
    get_active_manifest_hash,
    ground_answer,
    set_active_manifest_hash,
)


def _doc(source: str, page_content: str = "", **metadata):
    meta = {"source": source, **metadata}
    return SimpleNamespace(metadata=meta, page_content=page_content)


def test_chunk_id_is_stable_sha256_prefix():
    """chunk_id = sha256(source|content[:64])[:16] — no ingest-time ids."""
    title = "IITA 2018 - Production du niebe"
    content = "Les sacs PICS permettent un stockage hermétique non chimique du niébé."
    first = chunk_id(title, content)
    second = chunk_id(title, content)
    assert first == second
    assert len(first) == 16
    assert first == chunk_id(title, content + " extra after sixty-four chars")
    assert first != chunk_id(title, "different prefix")


def test_source_card_as_dict_keeps_flask_json_shape():
    """Farmer-facing /ask JSON still carries type, snippet, and country."""
    card = SourceCard(
        title="FAO Burkina Faso - politiques agricoles",
        publisher="FAO",
        year="2026",
        review_status="Revu, validation humaine à finaliser",
        url="https://www.fao.org/in-action/mafap/where-we-work/burkina-faso/en",
        type="Source web revue",
        snippet="La FAO signale AGRISurvey, FAOSTAT et CountrySTAT pour le Burkina Faso.",
        country="Burkina Faso",
    )
    assert card.as_dict() == {
        "title": "FAO Burkina Faso - politiques agricoles",
        "type": "Source web revue",
        "snippet": (
            "La FAO signale AGRISurvey, FAOSTAT et CountrySTAT "
            "pour le Burkina Faso."
        ),
        "publisher": "FAO",
        "year": "2026",
        "country": "Burkina Faso",
        "review_status": "Revu, validation humaine à finaliser",
        "url": "https://www.fao.org/in-action/mafap/where-we-work/burkina-faso/en",
    }


def test_source_card_as_dict_omits_empty_optional_fields():
    card = SourceCard(title="guide_mil.pdf", type="Base locale", snippet="")
    assert card.as_dict() == {
        "title": "guide_mil.pdf",
        "type": "Base locale",
        "snippet": "",
    }


def test_ground_answer_keeps_iita_and_drops_weak_secondary():
    """Port of the /ask noisy-source policy: keep IITA, drop Source faible."""
    docs = [
        _doc("Source faible", "Contenu secondaire peu lié au niébé."),
        _doc(
            "IITA 2018 - Production du niebe",
            "Les sacs PICS permettent un stockage hermétique non chimique du niébé.",
        ),
        _doc("Source moyenne", "Stockage et séchage des grains."),
    ]
    scores = {
        "IITA 2018 - Production du niebe": 0.43,
        "Source moyenne": 0.35,
        "Source faible": 0.18,
    }
    calls = {"n": 0}

    def score_lookup():
        calls["n"] += 1
        return scores

    grounded = ground_answer(
        "Comment stocker le niébé contre les bruches ?",
        docs,
        score_lookup=score_lookup,
    )

    assert calls["n"] == 1
    assert isinstance(grounded, GroundedAnswer)
    assert grounded.confidence == "Fort"
    titles = [card.title for card in grounded.sources]
    assert titles == ["IITA 2018 - Production du niebe"]
    assert "Source moyenne" not in titles
    assert "Source faible" not in titles
    assert len(grounded.retrieved_chunk_ids) == 3
    assert grounded.sources[0].as_dict()["title"] == "IITA 2018 - Production du niebe"


def test_ground_answer_demotes_fews_on_field_practice_query():
    """Livelihood/FEWS titles lose to an extension source on rotation/humidité."""
    docs = [
        _doc(
            "Burkina Faso - Profil des moyens d'existence (FEWS NET)",
            "Calendrier saisonnier et moyens d'existence au Burkina Faso.",
        ),
        _doc(
            "IITA 2018 - Production du niebe",
            "La rotation niébé-céréales restitue de l'azote et améliore la fertilité.",
        ),
    ]
    scores = {
        "Burkina Faso - Profil des moyens d'existence (FEWS NET)": 0.40,
        "IITA 2018 - Production du niebe": 0.38,
    }
    grounded = ground_answer(
        "Comment faire une rotation niébé céréales ?",
        docs,
        score_lookup=lambda: scores,
    )
    titles = [card.title for card in grounded.sources]
    assert "IITA 2018 - Production du niebe" in titles
    assert all("FEWS" not in title for title in titles)


def test_ground_answer_keeps_one_weak_card_at_faible():
    """SESSION.md policy: if only a weak title remains, keep it at Faible."""
    docs = [
        _doc(
            "Burkina Faso - Profil des moyens d'existence (FEWS NET)",
            "Calendrier saisonnier, semis et moyens d'existence.",
        ),
    ]
    scores = {
        "Burkina Faso - Profil des moyens d'existence (FEWS NET)": 0.40,
    }
    grounded = ground_answer(
        "Comment faire une rotation niébé ?",
        docs,
        score_lookup=lambda: scores,
    )
    assert len(grounded.sources) == 1
    assert "FEWS" in grounded.sources[0].title
    assert grounded.confidence == "Faible"


def test_ground_answer_count_fallback_when_score_lookup_empty():
    """Empty scores (vector store unavailable) use the count-based heuristic."""
    docs = [
        _doc("guide_mil.pdf", "Semez le mil au début de la saison des pluies."),
        _doc("calendrier.pdf", "Calendrier cultural du mil au Burkina."),
    ]
    grounded = ground_answer(
        "Quand semer le mil ?",
        docs,
        score_lookup=lambda: {},
    )
    titles = sorted(card.title for card in grounded.sources)
    assert titles == ["calendrier.pdf", "guide_mil.pdf"]
    assert grounded.confidence == "Fort"
    assert all(card.as_dict()["type"] == "Base locale" for card in grounded.sources)


def test_ground_answer_count_fallback_when_score_lookup_raises():
    docs = [_doc("guide_mil.pdf", "Semis du mil après une pluie utile.")]

    def broken_score_lookup():
        raise RuntimeError("score store unavailable")

    grounded = ground_answer(
        "Quand semer le mil ?",
        docs,
        score_lookup=broken_score_lookup,
    )
    assert [card.title for card in grounded.sources] == ["guide_mil.pdf"]
    assert grounded.confidence == "Moyen"


def test_ground_answer_preserves_reviewed_source_metadata():
    docs = [
        _doc(
            "FAO Burkina Faso - politiques agricoles",
            "La FAO signale AGRISurvey, FAOSTAT et CountrySTAT pour le Burkina Faso.",
            doc_type="scraped_web",
            publisher="FAO",
            year="2026",
            country="Burkina Faso",
            review_status="reviewed_by_codex_pending_human_review",
            source_url="https://www.fao.org/in-action/mafap/where-we-work/burkina-faso/en",
        )
    ]
    grounded = ground_answer(
        "Quelles données FAO existent ?",
        docs,
        score_lookup=lambda: {},
    )
    assert grounded.sources[0].as_dict() == {
        "title": "FAO Burkina Faso - politiques agricoles",
        "type": "Source web revue",
        "snippet": (
            "La FAO signale AGRISurvey, FAOSTAT et CountrySTAT "
            "pour le Burkina Faso."
        ),
        "publisher": "FAO",
        "year": "2026",
        "country": "Burkina Faso",
        "review_status": "Revu, validation humaine à finaliser",
        "url": "https://www.fao.org/in-action/mafap/where-we-work/burkina-faso/en",
    }


def test_source_rank_score_demotes_weak_handbook():
    strong = _source_rank_score("IITA 2018 - Production du niebe", 0.40)
    weak = _source_rank_score("Farmer's Handbook on Basic Agriculture", 0.40)
    assert strong > weak
    assert _is_weak_source_title("Agrobusiness au Burkina Faso")
    assert _is_weak_source_title(
        "Burkina Faso - Profil des moyens d'existence (FEWS NET)"
    )
    assert not _is_weak_source_title("ProSol 2020 - fertilite des sols")
    light = _source_rank_score("FEWS NET profile", 0.40, heavy=False)
    heavy = _source_rank_score("FEWS NET profile", 0.40, heavy=True)
    assert heavy < light
    assert _is_field_practice_query({"rotation", "niebe"})


def test_manifest_hash_roundtrip(monkeypatch):
    set_active_manifest_hash(None)
    assert get_active_manifest_hash() is None
    set_active_manifest_hash("abc123def4567890")
    assert get_active_manifest_hash() == "abc123def4567890"
    set_active_manifest_hash(None)
