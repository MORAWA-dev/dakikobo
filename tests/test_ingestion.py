"""Smoke tests for local knowledge ingestion."""

import os
import glob
import json

import pytest
from langchain_core.documents import Document

import config
import core.rag_pipeline as rag_pipeline
from core.rag_pipeline import (
    build_source_manifest,
    list_markdown_files,
    load_markdown_from_folder,
    load_pdfs_from_folder,
)

# A few documents we expect to ship in the knowledge base. If these are renamed
# or removed, the ingestion contract changed and the test should flag it.
EXPECTED_PDFS = {
    "farmer_training_manual.pdf",
    "fao_publication_i3760e.pdf",
    "csa_investment_plan_burkina_final.pdf",
}

EXPECTED_MARKDOWN = {
    "farmer_training_manual.md",
    "fao_publication_i3760e.md",
    "csa_investment_plan_burkina_final.md",
}


def test_expected_pdfs_present():
    found = {
        os.path.basename(p)
        for p in glob.glob(
            os.path.join(config.DATA_FOLDER, "**", "*.pdf"), recursive=True
        )
    }
    assert found, "no PDFs discovered under the Data folder"
    missing = EXPECTED_PDFS - found
    assert not missing, f"expected PDFs missing from ingestion: {missing}"


def test_expected_markdown_present():
    found = {
        os.path.basename(p)
        for p in glob.glob(
            os.path.join(config.MARKDOWN_FOLDER, "**", "*.md"), recursive=True
        )
    }
    assert found, "no Markdown discovered under the Markdown knowledge folder"
    missing = EXPECTED_MARKDOWN - found
    assert not missing, f"expected Markdown files missing from ingestion: {missing}"


def test_load_markdown_returns_documents():
    docs = load_markdown_from_folder(os.path.join("Data", "markdown", "scraped_reviewed"))
    assert len(docs) > 0, "Markdown ingestion produced no Documents"
    for d in docs:
        assert isinstance(d, Document)
        assert d.page_content.strip(), "Document has empty text"
        assert d.metadata.get("source"), "Document missing source metadata"
        assert d.metadata.get("source_file"), "Document missing source_file metadata"
        assert d.metadata.get("markdown_file"), "Document missing markdown_file metadata"
        assert d.metadata.get("data_format") == "markdown"
    original_sources = {os.path.basename(d.metadata["source_file"]) for d in docs}
    assert all(d.metadata["review_status"] == "reviewed_by_owner" for d in docs)


def test_load_markdown_preserves_review_metadata(tmp_path):
    source = tmp_path / "reviewed_web.md"
    source.write_text(
        """---
title: "Guide web revu"
source_file: "https://example.test/guide"
source_id: "example_source"
source_url: "https://example.test/guide"
doc_type: "scraped_web"
language: "fr"
country: "Burkina Faso"
publisher: "Source officielle"
license: "unknown"
review_status: "reviewed_by_owner"
scraped_at: "2026-07-02T10:00:00+00:00"
reviewed_at: "2026-07-02T11:00:00+00:00"
topics: "semis, pluie"
crops: "mil, sorgho"
---
# Guide web revu

Contenu agricole vérifié.
""",
        encoding="utf-8",
    )

    docs = load_markdown_from_folder(str(tmp_path))

    assert len(docs) == 1
    metadata = docs[0].metadata
    assert metadata["source"] == "Guide web revu"
    assert metadata["source_id"] == "example_source"
    assert metadata["source_url"] == "https://example.test/guide"
    assert metadata["doc_type"] == "scraped_web"
    assert metadata["review_status"] == "reviewed_by_owner"
    assert metadata["license"] == "unknown"
    assert metadata["topics"] == "semis, pluie"
    assert metadata["crops"] == "mil, sorgho"


def test_source_manifest_tracks_markdown_content(tmp_path):
    active = tmp_path / "active.md"
    skipped = tmp_path / "_index.md"
    approved_header = "---\ntitle: Guide\nsource_file: guide.pdf\nreview_status: reviewed_by_owner\n---\n"
    active.write_text(approved_header + "contenu A", encoding="utf-8")
    skipped.write_text("ignore", encoding="utf-8")

    files = list_markdown_files(str(tmp_path))
    manifest = build_source_manifest(
        files,
        source_type="Markdown",
        external_sources=["https://example.test/source"],
    )

    assert files == [str(active)]
    assert manifest["source_type"] == "Markdown"
    assert manifest["embedding_model"] == config.EMBEDDING_MODEL
    assert manifest["external_sources"] == ["https://example.test/source"]
    assert manifest["files"][0]["path"].endswith("active.md")
    assert manifest["files"][0]["bytes"] == len((approved_header + "contenu A").encode("utf-8"))

    first_hash = manifest["files"][0]["sha256"]
    active.write_text(approved_header + "contenu B", encoding="utf-8")
    changed = build_source_manifest(files, source_type="Markdown")

    assert changed["files"][0]["sha256"] != first_hash


def test_stale_vector_store_manifest_is_rejected(tmp_path, monkeypatch):
    vector_dir = tmp_path / "chroma"
    vector_dir.mkdir()
    (vector_dir / "source_manifest.json").write_text(
        json.dumps({"files": [{"path": "old.md"}]}),
        encoding="utf-8",
    )

    monkeypatch.setattr(rag_pipeline, "VECTORSTORE_DIR", str(vector_dir))
    monkeypatch.setattr(
        rag_pipeline,
        "load_vector_store",
        lambda: (_ for _ in ()).throw(AssertionError("stale store should not load")),
    )

    db = rag_pipeline.load_vector_store_if_usable({"files": [{"path": "new.md"}]})

    assert db is None


def test_load_pdfs_requires_review_then_preserves_provenance(tmp_path, monkeypatch):
    source = tmp_path / "guide.pdf"
    source.write_bytes(b"%PDF-test")
    monkeypatch.setattr(rag_pipeline, "extract_pdf_text", lambda path: "Conseil agricole")
    assert load_pdfs_from_folder(str(tmp_path)) == []
    source.with_suffix(".pdf.review.json").write_text(json.dumps({"review_status":"reviewed_by_owner", "title":"Guide", "source_file":"guide.pdf"}))
    docs = load_pdfs_from_folder(str(tmp_path))
    assert len(docs) == 1
    assert docs[0].metadata["review_status"] == "reviewed_by_owner"
    assert docs[0].page_content == "Conseil agricole"


def test_fetch_website_content_uses_configured_timeout(monkeypatch):
    calls = {}

    class FakeResponse:
        text = "page agricole"

        def raise_for_status(self):
            return None

    def fake_get(url, headers, timeout):
        calls["url"] = url
        calls["headers"] = headers
        calls["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(rag_pipeline, "WEB_FETCH_TIMEOUT_SECONDS", 2.5)
    monkeypatch.setattr(rag_pipeline.requests, "get", fake_get)

    docs = rag_pipeline.fetch_website_content("https://example.test")

    assert len(docs) == 1
    assert docs[0].page_content == "page agricole"
    assert docs[0].metadata["source"] == "https://example.test"
    assert calls["timeout"] == 2.5


def test_scope_metadata_is_preserved(tmp_path):
    source = tmp_path / "scoped.md"
    source.write_text(
        """---
title: "Document borné"
source_url: "https://example.test/scoped"
review_status: "reviewed_by_owner"
scope: "orientation générale ; pas de doses par parcelle"
---
Corps du document.
""",
        encoding="utf-8",
    )

    docs = load_markdown_from_folder(str(tmp_path))

    assert len(docs) == 1
    assert docs[0].metadata["scope"] == "orientation générale ; pas de doses par parcelle"


def test_quarantine_directory_wins_over_approval(tmp_path):
    from core.source_policy import eligible_source, quarantined_source

    quarantine = tmp_path / "_quarantine"
    quarantine.mkdir()
    source = quarantine / "rights_pending.md"
    source.write_text(
        """---
title: "Droits non confirmés"
source_url: "https://example.test/unclear"
review_status: "reviewed_by_owner"
---
Contenu dont les droits ne sont pas confirmés.
""",
        encoding="utf-8",
    )

    assert quarantined_source(source)
    assert not eligible_source(source)
    assert list(rag_pipeline.list_markdown_files(str(tmp_path))) == []


def test_rights_unclear_status_is_quarantined(tmp_path):
    from core.source_policy import eligible_source, quarantined_source

    source = tmp_path / "unclear.md"
    source.write_text(
        """---
title: "Droits incertains"
source_url: "https://example.test/unclear2"
review_status: "rights_unclear"
---
Contenu.
""",
        encoding="utf-8",
    )

    assert quarantined_source(source)
    assert not eligible_source(source)


def test_audit_script_default_output_is_canonical_undated():
    from scripts.audit_source_eligibility import DEFAULT_OUTPUT

    assert DEFAULT_OUTPUT.name == "SOURCE_ELIGIBILITY.md"
    assert DEFAULT_OUTPUT.parent.name == "reviews"
