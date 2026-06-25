# Gemini Suggestions for DakiKobo

Here is a set of proposed improvements for the DakiKobo project, organized into actionable sessions. Each session is designed to be completed in approximately 60-90 minutes.

---

## Session 1: Foundational Fixes & RAG Persistence

**Goal:** Stabilize the application by fixing critical bugs, cleaning up the codebase, and enabling a persistent, more capable RAG pipeline.

### 1. Plan

1.  **Fix Frontend Asset Paths:** Correct the hardcoded avatar and favicon paths in `static/js/index.js` and `templates/index.html` to correctly display logos and avatars.
2.  **Clean Up Deprecated Files:** Remove old, unused Python scripts (`chat1.py`, `chat2.py`) from the root directory.
3.  **Implement ChromaDB Persistence:** Modify the RAG pipeline to save the vector database to a local directory (`./db/chroma_db`). This avoids costly re-indexing on every server restart.
4.  **Enable Recursive PDF Loading:** Update the data loader to find and ingest PDFs from all subdirectories within `Data/knowledge_base/`, not just the top level.
5.  **Ingest New Documents:** Move the 7 pending documents into the knowledge base so they are included in the RAG system.

### 2. Code

**A. Fix Frontend Paths**

Apply this change to `static/js/index.js`:

```diff
--- a/static/js/index.js
+++ b/static/js/index.js
@@ -10,8 +10,8 @@
     function appendMessage(message, isUser) {
         var messageClass = isUser ? 'user-message' : 'bot-message';
         // Updated logo reference to DakiKobo
-        var logoHTML = isUser ? '' : '<div class="bot-logo"><img src="/static/robo.png" alt="DakiKobo Logo"></div>';
-        var userImageHTML = isUser ? '<div class="user-image"><img src="/static/user.png" alt="User"></div>' : '';
+        var logoHTML = isUser ? '' : '<div class="bot-logo"><img src="/static/images/bot_avatar.png" alt="DakiKobo Logo"></div>';
+        var userImageHTML = isUser ? '<div class="user-image"><img src="/static/images/user_avatar.png" alt="User"></div>' : '';
         var messageElement = $('<div class="message-container ' + (isUser ? 'user-container' : 'bot-container') + '">' + 
                             logoHTML + 
                             '<div class="message ' + messageClass + '"></div>' +

```

Apply this change to `templates/index.html`:

```diff
--- a/templates/index.html
+++ b/templates/index.html
@@ -7,7 +7,7 @@
     <link
       id="favicon"
       rel="shortcut icon"
-      href="{{ url_for('static', filename='logo.png') }}"
+      href="{{ url_for('static', filename='images/logo.png') }}"
       type="image/x-png"
     />
     <title>DakiKobo</title>
@@ -25,7 +25,7 @@
         <div class="logo-title">
           <div class="logo-circle">
             <img
-              src="{{ url_for('static', filename='logo.png') }}"
+              src="{{ url_for('static', filename='images/logo.png') }}"
               alt="DakiKobo Logo"
               class="logo-image"
             />

```

**B. Clean Up & Ingest New Documents (Shell Commands)**

Execute these commands in your terminal:

```bash
# Remove deprecated files
rm chat1.py chat2.py

# Organize and ingest new PDF documents
mkdir -p Data/knowledge_base/new_additions
mv Data/"New Folder With Items"/*.pdf Data/knowledge_base/new_additions/
```

**C. Enable Persistence and Recursive Loading**

Replace the content of `core/rag_pipeline.py` with this updated version. It adds persistence, recursive loading, and document source tracking.

```python
# core/rag_pipeline.py — RAG data ingestion, vector store, and TTS utilities

import os
import glob
import random
import string
from itertools import chain

import requests
import PyPDF2
import gtts
from flask import url_for

from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain_community.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddings,
)

from config import (
    EMBEDDING_MODEL,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    TTS_LANGUAGE,
    TTS_MAX_CHARS,
    AUDIO_OUTPUT_DIR,
    DB_PERSIST_DIR, # New config variable
)


# =================================================================
# WEB SCRAPING
# =================================================================

def fetch_website_content(url: str) -> list[Document]:
    """Fetch content from a URL and return it as a Document."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        # Return as a Document object with source metadata
        return [Document(page_content=response.text, metadata={"source": url})]
    except requests.exceptions.RequestException as e:
        print(f"Warning: Could not fetch {url}. Error: {e}")
        return []


# =================================================================
# PDF EXTRACTION
# =================================================================

def extract_pdf_documents(pdf_file: str) -> list[Document]:
    """Extract text from a PDF and return it as a list of Documents with metadata."""
    try:
        with open(pdf_file, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            text = "".join(page.extract_text() or "" for page in reader.pages)
            if not text.strip():
                print(f"Warning: No text extracted from {os.path.basename(pdf_file)}")
                return []
            # Create a Document for the entire PDF content
            return [Document(page_content=text, metadata={"source": os.path.basename(pdf_file)})]
    except Exception as e:
        print(f"Error reading PDF {pdf_file}: {e}")
        return []


def load_pdfs_from_folder(folder_path: str) -> list[Document]:
    """Return extracted text from every PDF found recursively in folder_path as Documents."""
    # Use glob with recursive=True to find all PDFs in subdirectories
    pdf_files = glob.glob(os.path.join(folder_path, "**/*.pdf"), recursive=True)
    print(f"Found {len(pdf_files)} PDF(s) in and under {folder_path}")
    
    # Process each file and flatten the list of lists of Documents
    return list(chain.from_iterable(extract_pdf_documents(f) for f in pdf_files))


# =================================================================
# TEXT SPLITTING & VECTOR STORE
# =================================================================

def split_documents(documents: list[Document]) -> list[Document]:
    """Split a list of Documents into smaller chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    return splitter.split_documents(documents)


def initialize_vector_store(documents: list[Document]):
    """
    Build or load a ChromaDB vector store from a list of Document objects.
    Returns None if no valid content is provided.
    """
    if not documents:
        print("FATAL: No documents to initialize vector store.")
        return None

    embedding_fn = SentenceTransformerEmbeddings(model_name=EMBEDDING_MODEL)
    
    # Check if the database directory exists to load it, otherwise create it
    if os.path.exists(DB_PERSIST_DIR):
        print(f"Loading existing ChromaDB from {DB_PERSIST_DIR}")
        db = Chroma(persist_directory=DB_PERSIST_DIR, embedding_function=embedding_fn)
    else:
        print(f"Creating new ChromaDB at {DB_PERSIST_DIR}")
        chunks = split_documents(documents)
        if not chunks:
            print("FATAL: No text chunks to add to vector store.")
            return None
        os.makedirs(DB_PERSIST_DIR, exist_ok=True)
        db = Chroma.from_documents(
            documents=chunks,
            embedding=embedding_fn,
            persist_directory=DB_PERSIST_DIR
        )
    return db


# =================================================================
# TEXT-TO-SPEECH (TTS)
# =================================================================

def _random_filename(length: int = 15) -> str:
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choice(chars) for _ in range(length)) + ".mp3"


def text_to_speech_to_static(text: str) -> str:
    """
    Convert text to an MP3 file saved under static/audio/.
    Returns the browser-accessible URL path, or '' on failure.
    """
    try:
        os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)
        truncated = text[:TTS_MAX_CHARS]
        filename = _random_filename()
        output_path = os.path.join(AUDIO_OUTPUT_DIR, filename)

        tts = gtts.gTTS(text=truncated, lang=TTS_LANGUAGE)
        tts.save(output_path)

        return url_for("static", filename="audio/" + filename)
    except Exception as e:
        print(f"Audio generation error: {e}")
        return ""

```

**D. Update `config.py`**

Add the `DB_PERSIST_DIR` variable.

```python
# In config.py

# ... other settings
DATA_FOLDER = "Data/knowledge_base"
DB_PERSIST_DIR = "db/chroma_db" # Add this line
# ... other settings
```

**E. Update `app.py`**

The logic for initialization changes slightly to handle the document objects.

```python
# In app.py

# ... imports

# =================================================================
# RAG INITIALIZATION — runs once at startup
# =================================================================

print("1. Loading documents...")
# Load PDFs recursively
pdf_docs = load_pdfs_from_folder(DATA_FOLDER)
# Fetch web content
website_docs = list(chain.from_iterable(fetch_website_content(url) for url in KNOWLEDGE_URLS))

all_docs = pdf_docs + website_docs
valid_doc_count = len(all_docs)

print(f"2. Initializing Vector Store ({valid_doc_count} documents)...")
db = initialize_vector_store(all_docs)

print("3. Setting up RetrievalQA chain...")
chain = setup_retrieval_qa(db)
print(f"✅ {BOT_NAME} is ready!")

# ... rest of app.py
```

### 3. Definition of Done

1.  Start the Flask server (`python app.py`).
2.  Observe the server logs: It should say "Creating new ChromaDB..." on the first run and "Loading existing ChromaDB..." on subsequent runs.
3.  The logs should show that it found more than 8 PDFs (including the newly moved ones).
4.  Open the web interface. The bot avatar, user avatar, and favicon should load correctly.
5.  Ask a question in French from the test list, like: `Quand planter le mil dans la zone du Sahel au Burkina Faso ?`
6.  Verify you get a coherent answer.

### 4. Risks

*   **Permissions:** The script might fail if it doesn't have write permissions to create the `db/chroma_db` directory.
*   **First Run Time:** The initial run will be slower as it has to process all PDFs and create the database. Subsequent runs will be much faster.

---
This concludes the suggestions for Session 1. I am ready to provide the next sessions when you are.
