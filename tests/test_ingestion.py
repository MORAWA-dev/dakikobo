"""Smoke tests for PDF ingestion."""

import os
import glob

from langchain_core.documents import Document

import config
from core.rag_pipeline import load_pdfs_from_folder

# A few documents we expect to ship in the knowledge base. If these are renamed
# or removed, the ingestion contract changed and the test should flag it.
EXPECTED_PDFS = {
    "farmer_training_manual.pdf",
    "fao_publication_i3760e.pdf",
    "csa_investment_plan_burkina_final.pdf",
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


def test_load_pdfs_returns_documents():
    docs = load_pdfs_from_folder(os.path.join("Data", "knowledge_base"))
    assert len(docs) > 0, "ingestion produced no Documents"
    for d in docs:
        assert isinstance(d, Document)
        assert d.page_content.strip(), "Document has empty text"
        assert d.metadata.get("source"), "Document missing source metadata"
    sources = {d.metadata["source"] for d in docs}
    assert "farmer_training_manual.pdf" in sources
