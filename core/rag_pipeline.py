# core/rag_pipeline.py — RAG data ingestion, vector store, and TTS utilities

import os
from core.source_policy import eligible_source, source_review, split_markdown_frontmatter
import glob
import fcntl
import stat
import hashlib
import json
import shutil
import tempfile
import time

import requests
import PyPDF2
import gtts
from flask import url_for

from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddings,
)

from config import (
    EMBEDDING_MODEL,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    TTS_PARTIAL_TTL_SECONDS,
    TTS_CACHE_MAX_BYTES,
    TTS_CACHE_TTL_SECONDS,
    TTS_LANGUAGE,
    TTS_MAX_CHARS,
    TTS_TIMEOUT_SECONDS,
    AUDIO_OUTPUT_DIR,
    VECTORSTORE_DIR,
    WEB_FETCH_TIMEOUT_SECONDS,
)


VECTORSTORE_MANIFEST = "source_manifest.json"


# =================================================================
# WEB SCRAPING
# =================================================================

def fetch_website_content(url: str) -> list[Document]:
    """Fetch raw HTML from a URL as a Document tagged with its source URL.

    Returns an empty list on failure.
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        response = requests.get(url, headers=headers, timeout=WEB_FETCH_TIMEOUT_SECONDS)
        response.raise_for_status()
        return [Document(page_content=response.text, metadata={"source": url})]
    except requests.exceptions.RequestException as e:
        print(f"Warning: Could not fetch {url}. Error: {e}")
        return []


# =================================================================
# LOCAL KNOWLEDGE EXTRACTION
# =================================================================

def _normalize_list_value(value: str) -> str:
    """Flatten a YAML-ish list like '[sorghum, millet]' to 'sorghum, millet'.

    Chroma metadata must be scalar, so list-valued frontmatter is stored as a
    clean comma-separated string. Plain scalars pass through unchanged.
    """
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    parts = [p.strip().strip("\"'") for p in value.split(",")]
    return ", ".join(p for p in parts if p)


def _source_label_for_markdown(md_file: str, metadata: dict[str, str]) -> str:
    title = metadata.get("title", "").strip()
    if title and len(title) >= 8:
        return title

    source_file = metadata.get("source_file", "").strip()
    if source_file:
        return os.path.basename(source_file)

    return os.path.basename(md_file)


def list_markdown_files(folder_path: str) -> list[str]:
    """Return ingestible Markdown files under folder_path."""
    return [
        f for f in sorted(
            glob.glob(os.path.join(folder_path, "**", "*.md"), recursive=True)
        )
        if not os.path.basename(f).startswith("_") and eligible_source(f)
    ]


def list_pdf_files(folder_path: str) -> list[str]:
    """Return PDF files under folder_path."""
    return [f for f in sorted(glob.glob(os.path.join(folder_path, "**", "*.pdf"), recursive=True)) if eligible_source(f)]


def _file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_source_manifest(
    file_paths: list[str],
    *,
    source_type: str,
    external_sources: list[str] | None = None,
) -> dict:
    """Build a stable manifest for the corpus used to create Chroma."""
    files = []
    for path in sorted(set(file_paths)):
        if not os.path.isfile(path):
            continue
        files.append(
            {
                "path": os.path.relpath(path).replace(os.sep, "/"),
                "bytes": os.path.getsize(path),
                "sha256": _file_sha256(path),
            }
        )

    return {
        "version": 1,
        "source_type": source_type,
        "embedding_model": EMBEDDING_MODEL,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "external_sources": sorted(external_sources or []),
        "files": files,
    }


def _manifest_path() -> str:
    return os.path.join(VECTORSTORE_DIR, VECTORSTORE_MANIFEST)


def _read_vector_store_manifest() -> dict | None:
    try:
        with open(_manifest_path(), encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"Warning: Could not read vector store manifest: {e}")
        return None


def _write_vector_store_manifest(manifest: dict | None) -> None:
    if manifest is None:
        return
    os.makedirs(VECTORSTORE_DIR, exist_ok=True)
    with open(_manifest_path(), "w", encoding="utf-8") as file:
        json.dump(manifest, file, ensure_ascii=False, indent=2, sort_keys=True)


def load_markdown_from_folder(folder_path: str) -> list[Document]:
    """Return a Document per readable Markdown file under folder_path.

    Files whose names begin with `_` are treated as manifests/indexes and skipped.
    Each Document keeps traceability back to the converted file and original PDF.
    """
    md_files = list_markdown_files(folder_path)
    print(f"Found {len(md_files)} Markdown file(s) in and under {folder_path}")

    docs = []
    for f in md_files:
        try:
            with open(f, encoding="utf-8") as file:
                raw_text = file.read()
        except Exception as e:
            print(f"Error reading Markdown {f}: {e}")
            continue

        metadata, body = split_markdown_frontmatter(raw_text)
        if body.strip():
            doc_metadata = {
                "source": _source_label_for_markdown(f, metadata),
                "source_file": metadata.get("source_file", os.path.basename(f)),
                "markdown_file": f,
                "data_format": "markdown",
            }
            for key in (
                "title",
                "doc_type",
                "language",
                "country",
                "page_count",
                "year",
                "publisher",
                "source_id",
                "source_url",
                "review_status",
                "license",
                "scraped_at",
                "reviewed_at",
            ):
                if metadata.get(key):
                    doc_metadata[key] = metadata[key]
            # List-valued tags drive crop/zone-aware retrieval and richer cards.
            for key in ("crops", "topics", "agroecological_zone"):
                if metadata.get(key):
                    doc_metadata[key] = _normalize_list_value(metadata[key])
            docs.append(Document(page_content=body, metadata=doc_metadata))
            status = "ok"
        else:
            status = "EMPTY — skipped"
        print(f"  - {os.path.relpath(f, folder_path)} ({status})")
    return docs


def extract_pdf_text(pdf_file: str) -> str:
    """Extract all text from a PDF file. Returns empty string on failure."""
    try:
        with open(pdf_file, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            return "".join(
                page.extract_text() or "" for page in reader.pages
            )
    except Exception as e:
        print(f"Error reading PDF {pdf_file}: {e}")
        return ""


def load_pdfs_from_folder(folder_path: str) -> list[Document]:
    """Return a Document per readable PDF found recursively under folder_path.

    Each Document carries metadata["source"] = the PDF filename, so retrieved
    chunks can be cited. Subfolders are included. An unreadable or empty PDF is
    logged and skipped (never crashes startup).
    """
    pdf_files = list_pdf_files(folder_path)
    print(f"Found {len(pdf_files)} PDF(s) in and under {folder_path}")
    docs = []
    for f in pdf_files:
        text = extract_pdf_text(f)
        if text.strip():
            docs.append(
                Document(page_content=text, metadata={"source": os.path.basename(f), **{k: v for k, v in source_review(f).items() if isinstance(v, (str, int, float, bool))}})
            )
            status = "ok"
        else:
            status = "EMPTY — skipped"
        print(f"  - {os.path.relpath(f, folder_path)} ({status})")
    return docs


# =================================================================
# TEXT SPLITTING & VECTOR STORE
# =================================================================

def split_documents(documents: list[Document]) -> list[Document]:
    """Split Documents into chunks, preserving each chunk's source metadata."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    return splitter.split_documents(documents)


def _embeddings():
    return SentenceTransformerEmbeddings(model_name=EMBEDDING_MODEL)


def vector_store_exists() -> bool:
    """True if a persisted Chroma store already exists on disk."""
    return os.path.isdir(VECTORSTORE_DIR) and bool(os.listdir(VECTORSTORE_DIR))


def clear_vector_store() -> None:
    """Remove the persisted Chroma store before a clean rebuild."""
    if os.path.isdir(VECTORSTORE_DIR):
        shutil.rmtree(VECTORSTORE_DIR)


def load_vector_store():
    """Load the persisted Chroma store from disk (no re-embedding)."""
    return Chroma(persist_directory=VECTORSTORE_DIR, embedding_function=_embeddings())


def load_vector_store_if_usable(expected_manifest: dict | None = None):
    """Load a persisted Chroma store only when its collection has documents."""
    if not vector_store_exists():
        return None
    if expected_manifest is not None:
        current_manifest = _read_vector_store_manifest()
        if current_manifest != expected_manifest:
            print("Warning: Existing vector store manifest is stale; rebuilding.")
            return None
    try:
        db = load_vector_store()
        count = db._collection.count()
    except Exception as e:
        print(f"Warning: Existing vector store is not usable: {e}")
        return None

    if count <= 0:
        print("Warning: Existing vector store has no documents; rebuilding.")
        return None

    print(f"1. Loaded existing vector store with {count} chunks.")
    return db


def initialize_vector_store(documents: list[Document], source_manifest: dict | None = None):
    """
    Build a persistent ChromaDB vector store from a list of Documents and save it
    to VECTORSTORE_DIR. Each chunk keeps its source metadata.
    Returns None if there is no content.
    """
    valid = [d for d in documents if d.page_content and d.page_content.strip()]
    if not valid:
        print("FATAL: No valid content to initialize vector store.")
        return None

    chunks = split_documents(valid)
    db = Chroma.from_documents(
        chunks,
        _embeddings(),
        persist_directory=VECTORSTORE_DIR,
        # Cosine keeps relevance scores in a stable, model-independent range so
        # SIMILARITY_THRESHOLD works regardless of the embedding model.
        collection_metadata={"hnsw:space": "cosine"},
    )
    _write_vector_store_manifest(source_manifest)
    return db


# =================================================================
# TEXT-TO-SPEECH (TTS)
# =================================================================

def _speech_filename(text: str, *, language: str = TTS_LANGUAGE) -> str:
    """Derive a stable filename from the spoken text.

    Random names meant every repeat of the same answer wrote another MP3, so
    ``static/audio/`` grew without bound and never reused work. Hashing the
    language plus the exact synthesized text makes identical answers collapse
    onto one file that can be served straight from disk.
    """
    digest = hashlib.sha256(f"{language}|{text}".encode("utf-8")).hexdigest()
    return f"tts_{digest[:32]}.mp3"


def _audio_cache_entries() -> list[tuple[float, int, str]]:
    """Return (mtime, size, path) for every generated MP3, oldest first."""
    entries = []
    try:
        names = os.listdir(AUDIO_OUTPUT_DIR)
    except OSError:
        return entries
    for name in names:
        if not name.endswith(".mp3"):
            continue
        path = os.path.join(AUDIO_OUTPUT_DIR, name)
        try:
            info = os.stat(path, follow_symlinks=False)
            if not stat.S_ISREG(info.st_mode):
                continue
        except OSError:
            continue
        entries.append((info.st_mtime, info.st_size, path))
    entries.sort(key=lambda entry: entry[0])
    return entries


def _prune_partial_audio(now: float) -> int:
    """Remove abandoned writes, never a file locked by a synthesizing worker."""
    removed = 0
    if TTS_PARTIAL_TTL_SECONDS <= 0:
        return removed
    for path in glob.glob(os.path.join(AUDIO_OUTPUT_DIR, ".tts-*.part")):
        try:
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(descriptor, "rb") as partial:
                fcntl.flock(partial, fcntl.LOCK_EX | fcntl.LOCK_NB)
                info = os.fstat(partial.fileno())
                if stat.S_ISREG(info.st_mode) and now - info.st_mtime > TTS_PARTIAL_TTL_SECONDS:
                    os.unlink(path)
                    removed += 1
        except OSError:
            # Locked, already removed, or inaccessible: let a later pass retry.
            continue
    return removed


def prune_audio_cache(*, keep: str = "", now: float | None = None) -> int:
    """Bound ``static/audio/`` by age and then by total size.

    Files older than ``TTS_CACHE_TTL_SECONDS`` are removed first. If the
    directory is still above ``TTS_CACHE_MAX_BYTES``, the least recently used
    files are removed until it fits. ``keep`` is never deleted so the response
    being served right now stays valid. Returns the number of files removed.
    """
    now = time.time() if now is None else now
    keep_path = os.path.abspath(keep) if keep else ""
    removed = _prune_partial_audio(now)

    entries = _audio_cache_entries()
    survivors: list[tuple[float, int, str]] = []
    for mtime, size, path in entries:
        if keep_path and os.path.abspath(path) == keep_path:
            survivors.append((mtime, size, path))
            continue
        if TTS_CACHE_TTL_SECONDS > 0 and (now - mtime) > TTS_CACHE_TTL_SECONDS:
            try:
                os.remove(path)
                removed += 1
            except OSError:
                survivors.append((mtime, size, path))
            continue
        survivors.append((mtime, size, path))

    if TTS_CACHE_MAX_BYTES <= 0:
        return removed

    total = sum(size for _, size, _ in survivors)
    for mtime, size, path in survivors:
        if total <= TTS_CACHE_MAX_BYTES:
            break
        if keep_path and os.path.abspath(path) == keep_path:
            continue
        try:
            os.remove(path)
        except OSError:
            continue
        total -= size
        removed += 1
    return removed


def _truncate_for_speech(text: str, max_chars: int) -> str:
    """Trim text to max_chars without cutting a word in half.

    Prefers to end on the last sentence boundary (.!?) within the limit; falls
    back to the last whitespace, so the audio never stops mid-word.
    """
    text = text.strip()
    if len(text) <= max_chars:
        return text

    window = text[:max_chars]
    cut = max(window.rfind(". "), window.rfind("! "), window.rfind("? "))
    if cut == -1:
        cut = window.rfind(" ")
    if cut == -1:
        return window  # single very long token; nothing to cut on
    # +1 keeps the sentence-ending punctuation when we cut on it
    return window[: cut + 1].strip()


def text_to_speech_to_static(text: str) -> str:
    """
    Convert text to an MP3 file saved under static/audio/.
    Returns the browser-accessible URL path, or '' on failure.

    The filename is derived from the spoken text, so an answer that was already
    voiced is served from disk without another gTTS call. Storage stays bounded
    by ``prune_audio_cache``.
    """
    try:
        os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)
        truncated = _truncate_for_speech(text, TTS_MAX_CHARS)
        filename = _speech_filename(truncated)
        output_path = os.path.join(AUDIO_OUTPUT_DIR, filename)

        if os.path.isfile(output_path) and os.path.getsize(output_path) > 0:
            # Mark as recently used so a popular answer is evicted last.
            try:
                os.utime(output_path, None)
            except OSError:
                pass
        else:
            # Write to a private temp file first: a partially written MP3 must
            # never be reachable under the deterministic name, including when a
            # second worker asks for the same answer concurrently.
            handle, temp_path = tempfile.mkstemp(
                dir=AUDIO_OUTPUT_DIR, prefix=".tts-", suffix=".part"
            )
            try:
                fcntl.flock(handle, fcntl.LOCK_EX)
                tts = gtts.gTTS(
                    text=truncated,
                    lang=TTS_LANGUAGE,
                    timeout=TTS_TIMEOUT_SECONDS,
                )
                tts.save(temp_path)
                os.replace(temp_path, output_path)
            except BaseException:
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
                raise
            finally:
                os.close(handle)

        # Bounding the directory must never fail the request that produced audio.
        try:
            prune_audio_cache(keep=output_path)
        except Exception as exc:
            print(f"Audio cleanup skipped: {exc}")

        return url_for("static", filename="audio/" + filename)
    except Exception as e:
        print(f"Audio generation skipped: {e}")
        return ""
