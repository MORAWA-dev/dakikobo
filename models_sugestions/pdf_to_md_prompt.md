# Prompt: Convert DakiKobo PDFs to RAG-ready Markdown

**Use in:** Cursor Composer 2.5 (preferred, it runs in the repo) or Grok. 
**Goal:** Turn every PDF in `Data/` into clean, metadata-rich Markdown optimized for RAG retrieval, via a reusable script, not by hand-transcription.

---

## Why a script and not manual transcription (read before delegating)

Several of these PDFs are 100+ pages (KIT book, GIZ program doc, country profile). Asking an LLM to read and retype them risks hallucinated numbers, which is fatal for a tool giving fertilizer doses. Make the model build a deterministic extraction pipeline. Use the LLM only for the optional cleanup pass on already-extracted text, never to invent content.

---

## PROMPT A — primary (paste into Cursor Composer 2.5)

> You are working in the DakiKobo repo. Build a reusable PDF-to-Markdown conversion pipeline for my RAG knowledge base. Do not transcribe PDFs yourself; write code that extracts text deterministically.
>
> **Task**
> Create `scripts/pdf_to_md.py` that converts every PDF under `Data/` (recurse into all subfolders, including `Data/knowledge_base/` and `Data/New Folder With Items/`) into one Markdown file each, written to `Data/markdown/` mirroring the source folder structure. Preserve the original filename, changing only the extension to `.md`.
>
> **Extraction approach (in this order of preference)**
> 1. Use `pymupdf4llm` as the primary extractor (`pip install pymupdf4llm`). It outputs Markdown with headings and tables preserved.
> 2. For any PDF where extracted text length is under ~200 characters per page on average, treat it as scanned/image-only: run OCR with `ocrmypdf` (French language pack, `-l fra`) into a temp searchable PDF first, then extract. If `ocrmypdf` is unavailable, log the file to `Data/markdown/_NEEDS_OCR.txt` and skip it rather than producing garbage.
> 3. Preserve tables as GitHub-flavored Markdown tables. Never flatten a table into a run-on sentence; tables carry the fertilizer doses and yield figures.
>
> **Cleaning rules (deterministic, in code)**
> - Strip repeated running headers/footers and standalone page numbers.
> - Collapse 3+ blank lines into one; fix hyphenation at line breaks (`agri-\nculture` becomes `agriculture`).
> - Keep the original language (mostly French). Do not translate.
> - Replace each image/figure with a placeholder line: `> [Figure: <caption if available, else 'no caption'>]`.
> - Do not summarize, paraphrase, or drop content. Extraction must be lossless for text.
>
> **Required YAML front matter at the top of every `.md`** (fill what you can detect; leave unknowns as `null`):
> ```yaml
> ---
> title: <document title from first page or filename>
> source_file: <original relative path, e.g. Data/knowledge_base/fao_publication_i3760e.pdf>
> doc_type: <one of: fao_report | csa_plan | training_manual | research_article | country_profile | program_doc | unknown>
> language: <fr | en | mixed>
> publisher: <organization if detectable, else null>
> year: <publication year if detectable, else null>
> country: Burkina Faso
> agroecological_zone: <Sahel | Sudanian Savanna | both | national | null>
> crops: [<any of: sorghum, millet, maize, cotton, cowpea, groundnut detected in the doc>]
> topics: [<short keywords, e.g. fertilization, sowing, pest, climate, storage>]
> page_count: <integer>
> extracted_with: <pymupdf4llm | ocrmypdf+pymupdf4llm>
> ---
> ```
>
> **Heading structure for retrieval**
> - Ensure a single `#` H1 (the document title) at the top, below the front matter.
> - Map the document's own section structure to `##` / `###`. If the PDF has no detectable headings, insert `##` headings at major topic breaks based on the table of contents or large font runs; do not invent section titles, use the document's own wording.
> - This heading hierarchy lets me chunk with a Markdown-header-aware splitter instead of blind character splitting.
>
> **Manifest**
> After converting all files, write `Data/markdown/_manifest.csv` with columns: `source_file, output_file, doc_type, language, page_count, chars_extracted, status` (status = `ok | ocr_used | needs_ocr | failed`).
>
> **Deliverables**
> 1. `scripts/pdf_to_md.py` (runnable as `python scripts/pdf_to_md.py`).
> 2. Add `pymupdf4llm` to `requirements.txt` (and note `ocrmypdf` as an optional system dependency in a comment).
> 3. Run it, then show me `Data/markdown/_manifest.csv` and the first 40 lines of two converted files: one from `knowledge_base/` and one large one from `New Folder With Items/`.
>
> **Definition of done**
> Every PDF in `Data/` has a matching `.md` in `Data/markdown/` with valid YAML front matter and at least one `#` heading; the manifest lists every file with a status; no file is empty; tables in the FAO and training-manual docs are visibly preserved as Markdown tables. Do not edit any app code (`app.py`, `core/`, `templates/`, `static/`) in this task.

---

## PROMPT B — optional cleanup pass (only if extraction is messy)

Run this only on files the manifest flags as poor quality. It edits already-extracted text; it must not add facts.

> Read `Data/markdown/<file>.md`. Improve only its formatting for RAG retrieval: fix broken headings, merge wrongly split paragraphs, repair tables that lost their pipes, and remove leftover header/footer noise. Rules: do not add, remove, translate, or reword any factual content; do not touch numbers, doses, dates, or place names; keep all French text as-is; preserve the YAML front matter exactly. Output the corrected file in place. If you are unsure whether something is noise or content, keep it.

---

## How this plugs back into your pipeline

Once `Data/markdown/` exists, update ingestion in `core/rag_pipeline.py` to load `.md` files and parse the YAML front matter into Chroma metadata (`source_file`, `doc_type`, `crops`, `agroecological_zone`, `year`). Then chunk with a header-aware splitter:

```python
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
# 1) split on headings to keep sections intact, 2) then size-split long sections
```

That gives you semantically coherent chunks plus rich metadata, which is the foundation for the citation chips and crop/zone filtering described in `claude.md`.

---

## Honest caveats

- `pymupdf4llm` is strong on born-digital PDFs and decent on tables. If a specific document's tables come out broken, the higher-fidelity option is `docling` (IBM) or `marker`, both heavier and best run on Colab Pro GPU. Try `pymupdf4llm` first; escalate only the files that fail.
- Scanned French PDFs need the Tesseract French pack (`tesseract-ocr-fra`). OCR output always needs a human spot-check before you trust doses or figures from it.
- Spot-check the `needs_review_01.pdf` / `needs_review_02.pdf` outputs manually; you still do not know what those documents are.
