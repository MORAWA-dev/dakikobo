# DakiKobo Deployment Guide

This app can be hosted as a Flask web service on Hugging Face Spaces, Render, Railway, Fly.io, Azure App Service, or any Docker-capable platform.

## Recommended Demo Path

If the budget is zero, start with Hugging Face Spaces using the Docker SDK:

- Free CPU Spaces are realistic for this app's Python/RAG dependency stack.
- Space secrets can hold `GROQ_API_KEY`, `GEMINI_API_KEY`, and `FLASK_SECRET_KEY`.
- The root `README.md` includes the Space metadata (`sdk: docker`, `app_port: 7860`).
- The included `Dockerfile` listens on port `7860`, which is the expected Space port.

Render or Railway are also good demo options if you later have a small monthly budget:

- They can deploy directly from GitHub.
- They provide HTTPS URLs for sharing.
- Environment variables can be configured in the dashboard.
- The included `Procfile` and `Dockerfile` give the platform a production start command.

For a longer-lived production system, use Azure App Service, Fly.io, or another provider where you can attach persistent storage or move the vector database to a managed service.

## Required Environment Variables

Set these in the hosting provider dashboard. Do not commit them to Git.

```text
GROQ_API_KEY=...
GEMINI_API_KEY=...
FLASK_SECRET_KEY=generate-a-long-random-secret
FLASK_DEBUG=false
REBUILD_VECTORSTORE=false
```

Optional:

```text
LLM_MODEL=llama-3.3-70b-versatile
VECTORSTORE_DIR=chroma_db
```

## Hugging Face Spaces

1. Create a new Space at Hugging Face.
2. Use the owner/account `kimcomehome`.
3. Name the Space `dakikobo`, so the public URL will be:

```text
https://huggingface.co/spaces/kimcomehome/dakikobo
```

4. Select **Docker** as the Space SDK.
5. Upload or push this repository to the Space repo.
6. In **Settings -> Secrets**, add:

```text
GROQ_API_KEY
GEMINI_API_KEY
FLASK_SECRET_KEY
```

7. In **Settings -> Variables**, add:

```text
FLASK_DEBUG=false
REBUILD_VECTORSTORE=false
PORT=7860
```

8. Push from this repo:

```bash
git remote add hf https://huggingface.co/spaces/kimcomehome/dakikobo
git push hf main
```

9. Wait for the Space to build, then open `/healthz` to confirm the Flask process is alive.
10. Ask one warm-up RAG question before sharing the link; the first real question may download/load embeddings and build `chroma_db`.

Free Space caveats:

- Free Spaces may sleep when inactive.
- The runtime disk is not a production database; feedback CSV and generated audio should be treated as temporary.
- Keep `.env`, API keys, and generated files out of Git.
- If the Space is public, source code is public, but secrets configured in the Space settings stay hidden.

## Generic Build And Start

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 180
```

Health check path:

```text
/healthz
```

## Important Production Notes

- The first real RAG question may be slow because the app loads the embedding model and vector store lazily.
- Keep `Data/` available on the deployed service if the vector store must be rebuilt.
- Do not commit `.env`, `chroma_db/`, generated audio files, or feedback CSV files.
- A serious production version should move feedback from CSV to a database and move generated audio to object storage.
- If traffic grows, separate ingestion/vector-store building from the Flask web process.
