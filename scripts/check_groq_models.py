"""List chat models the configured Groq key can currently serve.

Temporary diagnostic helper: run after a Groq model decommission to see which
model IDs are still available before updating `LLM_MODEL` in config.py.

Usage:
    python scripts/check_groq_models.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

from dotenv import load_dotenv

MODELS_URL = "https://api.groq.com/openai/v1/models"


def main() -> int:
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        print("GROQ_API_KEY is not set in .env")
        return 1

    print(f"key loaded: yes (length {len(api_key)})")

    # Groq/Cloudflare rejects default Python user agents with HTTP 403, which is
    # why the app pins GROQ_USER_AGENT. Send the same header here.
    user_agent = os.getenv("GROQ_USER_AGENT", "Mozilla/5.0 DakiKobo/1.0")
    request = urllib.request.Request(
        MODELS_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "User-Agent": user_agent,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code} from Groq: {exc.read().decode('utf-8', 'replace')[:400]}")
        return 1
    except Exception as exc:  # noqa: BLE001 - diagnostic script
        print(f"request failed: {type(exc).__name__}: {exc}")
        return 1

    models = payload.get("data", [])
    if not models:
        print(f"unexpected response: {json.dumps(payload)[:400]}")
        return 1

    audio, chat = [], []
    for model in models:
        model_id = model.get("id", "")
        bucket = audio if ("whisper" in model_id or "tts" in model_id) else chat
        bucket.append((model_id, model.get("context_window"), model.get("owned_by")))

    print(f"\nCHAT MODELS ({len(chat)}):")
    for model_id, context_window, owner in sorted(chat):
        print(f"  {model_id:<45} ctx={context_window:<9} owner={owner}")

    print(f"\nAUDIO MODELS ({len(audio)}):")
    for model_id, _, owner in sorted(audio):
        print(f"  {model_id:<45} owner={owner}")

    available = {model_id for model_id, _, _ in chat + audio}
    print("\nCURRENTLY CONFIGURED:")
    for env_var, default in (
        ("LLM_MODEL", "llama-3.3-70b-versatile"),
        ("STT_MODEL", "whisper-large-v3-turbo"),
    ):
        configured = os.getenv(env_var, default)
        status = "OK" if configured in available else "MISSING / DECOMMISSIONED"
        print(f"  {env_var}={configured} -> {status}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
