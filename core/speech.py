"""Speech-to-text helpers for DakiKobo voice input."""

from groq import Groq

from config import (
    GROQ_API_KEY,
    GROQ_USER_AGENT,
    STT_LANGUAGE,
    STT_MODEL,
    STT_TIMEOUT_SECONDS,
)


class SpeechTranscriptionError(RuntimeError):
    """Raised when speech transcription cannot be completed."""


def is_configured() -> bool:
    return bool(GROQ_API_KEY)


def transcribe_audio(
    audio_bytes: bytes,
    *,
    filename: str = "question.webm",
    mime_type: str = "audio/webm",
) -> str:
    if not is_configured():
        raise SpeechTranscriptionError("GROQ_API_KEY is not configured.")
    if not audio_bytes:
        raise SpeechTranscriptionError("Audio payload is empty.")

    client = Groq(
        api_key=GROQ_API_KEY,
        timeout=STT_TIMEOUT_SECONDS,
        default_headers={"User-Agent": GROQ_USER_AGENT},
    )
    try:
        transcript = client.audio.transcriptions.create(
            model=STT_MODEL,
            file=(filename or "question.webm", audio_bytes, mime_type or "audio/webm"),
            language=STT_LANGUAGE,
            response_format="json",
            temperature=0,
            prompt=(
                "Question courte en français sur l'agriculture au Burkina Faso: "
                "mil, sorgho, maïs, niébé, arachide, sol, engrais, météo ou maladies."
            ),
        )
    except Exception as exc:
        raise SpeechTranscriptionError(str(exc)) from exc

    text = getattr(transcript, "text", "")
    return " ".join((text or "").split())
