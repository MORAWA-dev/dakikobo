"""Quick check that your GEMINI_API_KEY works.

Usage:
    python scripts/test_gemini.py

It loads GEMINI_API_KEY from your .env, calls the Gemini REST API, and prints a
clear PASS/FAIL with the server's error message if something is wrong. No extra
dependencies needed (uses requests).
"""

import os
import sys

import requests
from dotenv import load_dotenv

API_ROOT = "https://generativelanguage.googleapis.com/v1beta"


def _mask(value: str) -> str:
    if not value:
        return "<EMPTY>"
    return f"{value[:4]}...{value[-4:]} (len {len(value)})"


def main() -> int:
    load_dotenv()
    key = os.getenv("GEMINI_API_KEY", "").strip()

    print("GEMINI_API_KEY:", _mask(key))
    if not key:
        print("❌ No GEMINI_API_KEY found in .env")
        return 1

    # 1) Auth check: list available models.
    try:
        r = requests.get(f"{API_ROOT}/models", params={"key": key}, timeout=20)
    except requests.RequestException as e:
        print(f"❌ Network error: {e}")
        return 1

    if r.status_code != 200:
        print(f"❌ Key rejected (HTTP {r.status_code}).")
        print("   Server says:", r.text[:400])
        return 1

    models = [m.get("name", "") for m in r.json().get("models", [])]
    vision = [
        m for m in models
        if any(tag in m for tag in ("flash", "pro")) and "embedding" not in m
    ]
    print(f"✅ Key authenticates. {len(models)} models available.")
    if vision:
        print("   Vision-capable (examples):", ", ".join(vision[:5]))

    # 2) Tiny generation call to confirm end-to-end usage works.
    # Prefer the model the app actually uses (config.GEMINI_MODEL); fall back to a
    # known-good flash model, then any vision model that was listed.
    try:
        from config import GEMINI_MODEL as _app_model
    except Exception:
        _app_model = "gemini-2.5-flash"
    preferred = [_app_model, "gemini-2.5-flash", "gemini-flash-latest"]
    model = next((m for m in preferred if any(m in mm for mm in models)), None)
    if model is None and vision:
        model = vision[0].split("/")[-1]
    if model:
        print(f"   Testing generation with: {model}")
        payload = {
            "contents": [
                {"parts": [{"text": "Réponds en un mot: bonjour"}]}
            ]
        }
        gen = requests.post(
            f"{API_ROOT}/models/{model}:generateContent",
            params={"key": key},
            json=payload,
            timeout=30,
        )
        if gen.status_code == 200:
            try:
                text = gen.json()["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError):
                text = "<no text>"
            print(f"✅ Generation works ({model}). Reply: {text.strip()[:60]}")
        else:
            print(f"⚠️  Auth OK but generation failed (HTTP {gen.status_code}).")
            print("   Server says:", gen.text[:400])

    print("\nResult: ✅ GEMINI_API_KEY is working.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
