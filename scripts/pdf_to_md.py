#!/usr/bin/env python3
"""
pdf_to_md.py - Convert DakiKobo PDFs to RAG-ready Markdown.

Deterministic extraction (no LLM, no hallucination). Uses pdfplumber for text
and tables. Writes one .md per PDF into Data/markdown/ mirroring the source
tree, each with YAML front matter, plus Data/markdown/_manifest.csv.

Usage:
    python scripts/pdf_to_md.py            # convert everything under Data/
    python scripts/pdf_to_md.py --src Data --out Data/markdown

Notes:
- Scanned/image-only PDFs (very little extractable text) are flagged
  status=needs_ocr in the manifest and written as a stub. Run OCR on those
  separately:  ocrmypdf -l fra input.pdf output.pdf
- pymupdf4llm gives slightly better heading detection; if you can install it
  locally, swap extract_page_text() for pymupdf4llm.to_markdown(). pdfplumber
  is used here because it needs no native build and excels at tables.
"""

import argparse
import csv
import os
import re
import sys
import glob
import time
import datetime
from collections import Counter

import pdfplumber
import pypdf

TABLE_TIME_BUDGET = 18   # seconds spent on table extraction per file, then stop
TABLE_MAX_PAGES = 45     # skip pdfplumber tables on docs larger than this (too slow)

# ---- domain vocabulary (FR + EN) -------------------------------------------
CROP_TERMS = {
    "sorghum": ["sorgho", "sorghum"],
    "millet": ["mil ", "millet", "petit mil"],
    "maize": ["maïs", "mais", "maize", "corn"],
    "cotton": ["coton", "cotton"],
    "cowpea": ["niébé", "niebe", "cowpea", "vigna"],
    "groundnut": ["arachide", "groundnut", "peanut"],
}
TOPIC_TERMS = {
    "fertilization": ["engrais", "fertilis", "npk", "urée", "uree", "fumure"],
    "sowing": ["semis", "semer", "sowing", "planting", "date de semis"],
    "pest_disease": ["maladie", "ravageur", "pest", "disease", "insecte", "nuisible"],
    "climate": ["climat", "pluie", "pluviom", "sécheresse", "secheresse", "climate", "rainfall"],
    "soil": ["sol ", "fertilité", "fertilite", "soil"],
    "storage": ["stockage", "conservation", "storage", "post-récolte", "post-recolte"],
    "yield": ["rendement", "yield", "production"],
}
FR_STOP = re.compile(r"\b(le|la|les|des|une|dans|pour|avec|sont|cette|aux|est|et)\b", re.I)
EN_STOP = re.compile(r"\b(the|and|of|to|with|are|this|for|is|in)\b", re.I)


def detect_doc_type(name: str) -> str:
    n = name.lower()
    if "fao" in n:
        return "fao_report"
    if "csa" in n or "investment" in n:
        return "csa_plan"
    if "manual" in n or "handbook" in n or "formation" in n:
        return "training_manual"
    if "article" in n or "agronomy" in n or "growth_pole" in n or "analysis" in n:
        return "research_article"
    if "profile" in n or "country" in n or "bf_profile" in n:
        return "country_profile"
    if "giz" in n or "programme" in n or "program" in n:
        return "program_doc"
    if "menages" in n or "household" in n or "caract" in n:
        return "survey_report"
    return "unknown"


def detect_language(text: str) -> str:
    fr = len(FR_STOP.findall(text))
    en = len(EN_STOP.findall(text))
    if fr == 0 and en == 0:
        return "unknown"
    if fr > en * 1.3:
        return "fr"
    if en > fr * 1.3:
        return "en"
    return "mixed"


def detect_list(text_low: str, table: dict) -> list:
    found = []
    for label, terms in table.items():
        if any(t in text_low for t in terms):
            found.append(label)
    return found


def find_repeated_lines(pages_text: list) -> set:
    """Lines appearing on many pages are headers/footers; drop them."""
    counts = Counter()
    for pt in pages_text:
        for ln in {l.strip() for l in pt.splitlines() if l.strip()}:
            if len(ln) < 90:
                counts[ln] += 1
    n = len(pages_text)
    if n < 4:
        return set()
    return {ln for ln, c in counts.items() if c >= max(3, int(n * 0.4))}


def clean_text(text: str, repeated: set) -> str:
    out = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            out.append("")
            continue
        if s in repeated:
            continue
        if re.fullmatch(r"[-–—\s]*\d{1,4}[-–—\s]*", s):  # bare page numbers
            continue
        out.append(ln.rstrip())
    txt = "\n".join(out)
    txt = re.sub(r"(\w)[-­]\n(\w)", r"\1\2", txt)   # de-hyphenate line breaks
    txt = re.sub(r"\n{3,}", "\n\n", txt)                  # collapse blank runs
    return txt.strip()


def promote_headings(text: str) -> str:
    """Conservative: turn numbered or ALL-CAPS standalone lines into ## headings."""
    lines = text.splitlines()
    out = []
    for ln in lines:
        s = ln.strip()
        is_numbered = bool(re.match(r"^\d+(\.\d+)*[\.\)]?\s+\S", s)) and len(s) < 80
        is_caps = s.isupper() and 3 < len(s) < 70 and any(c.isalpha() for c in s)
        if (is_numbered or is_caps) and not s.startswith("#"):
            out.append(f"## {s}")
        else:
            out.append(ln)
    return "\n".join(out)


def table_to_md(tbl) -> str:
    rows = [[(c or "").replace("\n", " ").strip() for c in r] for r in tbl if r]
    rows = [r for r in rows if any(cell for cell in r)]
    if len(rows) < 2:
        return ""
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    head = "| " + " | ".join(rows[0]) + " |"
    sep = "| " + " | ".join("---" for _ in range(width)) + " |"
    body = "\n".join("| " + " | ".join(r) + " |" for r in rows[1:])
    return f"{head}\n{sep}\n{body}"


def yaml_front_matter(meta: dict) -> str:
    def fmt(v):
        if v is None:
            return "null"
        if isinstance(v, list):
            return "[" + ", ".join(v) + "]"
        if isinstance(v, str) and (":" in v or v == ""):
            return '"' + v.replace('"', "'") + '"'
        return str(v)
    lines = ["---"]
    for k, v in meta.items():
        lines.append(f"{k}: {fmt(v)}")
    lines.append("---")
    return "\n".join(lines)


def convert(pdf_path: str, src_root: str, out_root: str) -> dict:
    rel = os.path.relpath(pdf_path, src_root)
    base = os.path.basename(pdf_path)
    rec = {"source_file": pdf_path, "output_file": "", "doc_type": "",
           "language": "", "page_count": 0, "chars_extracted": 0, "status": "failed"}
    try:
        # --- text via pypdf (fast, same engine the app already uses) ---
        pages_text = []
        reader = pypdf.PdfReader(pdf_path)
        rec["page_count"] = len(reader.pages)
        for pg in reader.pages:
            try:
                pages_text.append(pg.extract_text() or "")
            except Exception:
                pages_text.append("")

        # --- tables via pdfplumber, bounded by a time budget ---
        all_tables, tables_truncated = [], False
        tbl_start = time.time()
        if rec["page_count"] > TABLE_MAX_PAGES:
            tables_truncated = True   # too big; text-only for speed
        try:
            if rec["page_count"] > TABLE_MAX_PAGES:
                raise StopIteration
            with pdfplumber.open(pdf_path) as pdf:
                for pg in pdf.pages:
                    if time.time() - tbl_start > TABLE_TIME_BUDGET:
                        tables_truncated = True
                        break
                    try:
                        for t in (pg.extract_tables() or []):
                            md = table_to_md(t)
                            if md:
                                all_tables.append(md)
                    except Exception:
                        pass
        except Exception:
            pass

        raw = "\n".join(pages_text)
        rec["chars_extracted"] = len(raw.strip())
        avg = rec["chars_extracted"] / max(1, rec["page_count"])

        out_path = os.path.join(out_root, os.path.splitext(rel)[0] + ".md")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        rec["output_file"] = out_path
        rec["doc_type"] = detect_doc_type(base)
        rec["language"] = detect_language(raw) if raw.strip() else "unknown"

        # scanned / image-only detection
        if avg < 120:
            rec["status"] = "needs_ocr"
            meta = {"title": os.path.splitext(base)[0], "source_file": rel,
                    "doc_type": rec["doc_type"], "language": "unknown",
                    "country": "Burkina Faso", "page_count": rec["page_count"],
                    "extracted_with": "none", "status": "needs_ocr"}
            stub = (yaml_front_matter(meta) + f"\n\n# {os.path.splitext(base)[0]}\n\n"
                    "> [This PDF appears to be scanned / image-only. Run OCR before "
                    "ingestion:  `ocrmypdf -l fra \"" + rel + "\" out.pdf`]\n")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(stub)
            return rec

        repeated = find_repeated_lines(pages_text)
        body = promote_headings(clean_text(raw, repeated))

        # title = first substantive line
        title = next((l.strip() for l in body.splitlines()
                      if len(l.strip()) > 6 and not l.startswith("#")),
                     os.path.splitext(base)[0])
        low = raw.lower()
        meta = {
            "title": title[:120],
            "source_file": rel,
            "doc_type": rec["doc_type"],
            "language": rec["language"],
            "country": "Burkina Faso",
            "crops": detect_list(low, CROP_TERMS) or None,
            "topics": detect_list(low, TOPIC_TERMS) or None,
            "page_count": rec["page_count"],
            "chars": rec["chars_extracted"],
            "extracted_with": "pdfplumber",
            "converted": datetime.date.today().isoformat(),
        }

        parts = [yaml_front_matter(meta), "", f"# {title[:120]}", "", body]
        if all_tables:
            note = ("> [Table extraction was time-capped; some tables from later "
                    "pages may be missing. Full text is complete.]\n"
                    if tables_truncated else "")
            parts += ["", "## Tables extraites", "", note] + \
                     [f"{t}\n" for t in all_tables]
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(parts).strip() + "\n")

        rec["status"] = "ok"
        return rec
    except Exception as e:
        rec["status"] = f"failed: {e}"
        return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="Data")
    ap.add_argument("--out", default="Data/markdown")
    ap.add_argument("--resume", action="store_true",
                    help="skip PDFs whose .md output already exists")
    args = ap.parse_args()

    pdfs = sorted(glob.glob(os.path.join(args.src, "**", "*.pdf"), recursive=True))
    print(f"Found {len(pdfs)} PDF(s) under {args.src}/", flush=True)
    os.makedirs(args.out, exist_ok=True)

    man = os.path.join(args.out, "_manifest.csv")
    fields = ["source_file", "output_file", "doc_type", "language",
              "page_count", "chars_extracted", "status"]
    if not os.path.exists(man):
        with open(man, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=fields).writeheader()

    for i, p in enumerate(pdfs, 1):
        rel = os.path.relpath(p, args.src)
        out_path = os.path.join(args.out, os.path.splitext(rel)[0] + ".md")
        if args.resume and os.path.exists(out_path):
            print(f"[{i}/{len(pdfs)}] {os.path.basename(p)} ... skip (exists)", flush=True)
            continue
        print(f"[{i}/{len(pdfs)}] {os.path.basename(p)} ...", flush=True)
        rec = convert(p, args.src, args.out)
        print(f"      -> {rec['status']}  ({rec['page_count']}p, "
              f"{rec['chars_extracted']} chars)", flush=True)
        with open(man, "a", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=fields).writerow(rec)
    print("\nPASS COMPLETE.", flush=True)


if __name__ == "__main__":
    main()
