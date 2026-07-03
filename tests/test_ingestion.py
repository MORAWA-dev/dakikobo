"""Smoke tests for local knowledge ingestion."""

import os
import glob

import pytest
from langchain_core.documents import Document

import config
import core.rag_pipeline as rag_pipeline
from core.rag_pipeline import load_markdown_from_folder, load_pdfs_from_folder

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
    docs = load_markdown_from_folder(os.path.join("Data", "markdown", "knowledge_base"))
    assert len(docs) > 0, "Markdown ingestion produced no Documents"
    for d in docs:
        assert isinstance(d, Document)
        assert d.page_content.strip(), "Document has empty text"
        assert d.metadata.get("source"), "Document missing source metadata"
        assert d.metadata.get("source_file"), "Document missing source_file metadata"
        assert d.metadata.get("markdown_file"), "Document missing markdown_file metadata"
        assert d.metadata.get("data_format") == "markdown"
    original_sources = {os.path.basename(d.metadata["source_file"]) for d in docs}
    assert "farmer_training_manual.pdf" in original_sources


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
review_status: "reviewed_by_codex"
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
    assert metadata["review_status"] == "reviewed_by_codex"
    assert metadata["license"] == "unknown"
    assert metadata["topics"] == "semis, pluie"
    assert metadata["crops"] == "mil, sorgho"


def test_load_pdfs_returns_documents():
    folder = os.path.join("Data", "knowledge_base")
    docs = load_pdfs_from_folder(folder)
    if not docs:
        pdf_files = glob.glob(os.path.join(folder, "*.pdf"))
        lfs_pointers = [
            p for p in pdf_files
            if open(p, "rb").read(80).startswith(
                b"version https://git-lfs.github.com/spec/v1"
            )
        ]
        if pdf_files and len(lfs_pointers) == len(pdf_files):
            pytest.skip(
                "PDF fallback files are Git LFS pointers in this checkout; "
                "Markdown ingestion is the primary deployed path."
            )
    assert len(docs) > 0, "ingestion produced no Documents"
    for d in docs:
        assert isinstance(d, Document)
        assert d.page_content.strip(), "Document has empty text"
        assert d.metadata.get("source"), "Document missing source metadata"
    sources = {d.metadata["source"] for d in docs}
    assert "farmer_training_manual.pdf" in sources


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
