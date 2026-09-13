"""Tests for TTS generation behavior without live gTTS calls."""

from pathlib import Path

import app as app_module
from core import rag_pipeline


def test_tts_passes_timeout_and_returns_static_url(tmp_path, monkeypatch):
    calls = {}

    class FakeGTTS:
        def __init__(self, text, lang, timeout):
            calls["text"] = text
            calls["lang"] = lang
            calls["timeout"] = timeout

        def save(self, output_path):
            Path(output_path).write_bytes(b"fake mp3")

    monkeypatch.setattr(rag_pipeline.gtts, "gTTS", FakeGTTS)
    monkeypatch.setattr(rag_pipeline, "AUDIO_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(rag_pipeline, "TTS_TIMEOUT_SECONDS", 3.5)

    with app_module.app.test_request_context("/"):
        audio_url = rag_pipeline.text_to_speech_to_static("Bonjour les producteurs.")

    assert audio_url.startswith("/static/audio/")
    assert audio_url.endswith(".mp3")
    assert calls == {
        "text": "Bonjour les producteurs.",
        "lang": "fr",
        "timeout": 3.5,
    }
    assert list(tmp_path.glob("*.mp3"))


def test_tts_failure_returns_empty_audio_url(tmp_path, monkeypatch):
    class FailingGTTS:
        def __init__(self, text, lang, timeout):
            pass

        def save(self, output_path):
            raise TimeoutError("gTTS took too long")

    monkeypatch.setattr(rag_pipeline.gtts, "gTTS", FailingGTTS)
    monkeypatch.setattr(rag_pipeline, "AUDIO_OUTPUT_DIR", str(tmp_path))

    with app_module.app.test_request_context("/"):
        audio_url = rag_pipeline.text_to_speech_to_static("Bonjour.")

    assert audio_url == ""
    assert list(tmp_path.glob("*.mp3")) == []


def test_tts_truncation_prefers_sentence_boundary():
    text = "Première phrase. Deuxième phrase longue avec beaucoup de détails."

    assert rag_pipeline._truncate_for_speech(text, 30) == "Première phrase."



# =====================================================================
# Audit regression — finding 8: bounded audio storage
# =====================================================================

import os
import time


class _CountingGTTS:
    """Records how many syntheses were actually performed."""

    calls = 0

    def __init__(self, text, lang, timeout):
        type(self).calls += 1
        self.text = text

    def save(self, output_path):
        Path(output_path).write_bytes(b"fake mp3 " + self.text.encode("utf-8"))


def _install_tts(monkeypatch, tmp_path, *, ttl=3600.0, max_bytes=64 * 1024 * 1024):
    _CountingGTTS.calls = 0
    monkeypatch.setattr(rag_pipeline.gtts, "gTTS", _CountingGTTS)
    monkeypatch.setattr(rag_pipeline, "AUDIO_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(rag_pipeline, "TTS_CACHE_TTL_SECONDS", ttl)
    monkeypatch.setattr(rag_pipeline, "TTS_CACHE_MAX_BYTES", max_bytes)


def test_identical_answers_reuse_one_deterministic_file(tmp_path, monkeypatch):
    """Random filenames meant every repeat wrote another MP3 forever."""
    _install_tts(monkeypatch, tmp_path)

    with app_module.app.test_request_context("/"):
        first = rag_pipeline.text_to_speech_to_static("Semez après une pluie utile.")
        second = rag_pipeline.text_to_speech_to_static("Semez après une pluie utile.")

    assert first == second
    assert len(list(tmp_path.glob("*.mp3"))) == 1
    # The second call was served from disk without another synthesis.
    assert _CountingGTTS.calls == 1


def test_filename_is_derived_from_the_answer_text(tmp_path, monkeypatch):
    _install_tts(monkeypatch, tmp_path)

    with app_module.app.test_request_context("/"):
        first = rag_pipeline.text_to_speech_to_static("Réponse une.")
        second = rag_pipeline.text_to_speech_to_static("Réponse deux.")

    assert first != second
    assert len(list(tmp_path.glob("*.mp3"))) == 2
    # Stable across processes: recomputing the name gives the same value.
    assert rag_pipeline._speech_filename("Réponse une.") in first
    assert rag_pipeline._speech_filename("Réponse une.") == rag_pipeline._speech_filename(
        "Réponse une."
    )


def test_expired_audio_is_pruned(tmp_path, monkeypatch):
    _install_tts(monkeypatch, tmp_path, ttl=60.0)
    stale = tmp_path / "tts_stale.mp3"
    stale.write_bytes(b"old")
    old = time.time() - 3600
    os.utime(stale, (old, old))

    with app_module.app.test_request_context("/"):
        fresh = rag_pipeline.text_to_speech_to_static("Conseil récent.")

    assert not stale.exists(), "audio older than the TTL was not pruned"
    assert (tmp_path / Path(fresh).name).exists()


def test_size_cap_evicts_least_recently_used_audio(tmp_path, monkeypatch):
    # Cap small enough that only a couple of files fit.
    _install_tts(monkeypatch, tmp_path, ttl=0, max_bytes=120)
    now = time.time()
    for index in range(6):
        path = tmp_path / f"tts_old_{index}.mp3"
        path.write_bytes(b"x" * 40)
        stamp = now - (600 - index)
        os.utime(path, (stamp, stamp))

    with app_module.app.test_request_context("/"):
        kept = rag_pipeline.text_to_speech_to_static("Nouveau conseil.")

    total = sum(p.stat().st_size for p in tmp_path.glob("*.mp3"))
    assert total <= 120, f"audio directory stayed above the cap ({total} bytes)"
    # The file just produced is never the one evicted.
    assert (tmp_path / Path(kept).name).exists()
    # Eviction is least-recently-used: the oldest names go first.
    assert not (tmp_path / "tts_old_0.mp3").exists()


def test_prune_is_disabled_when_both_bounds_are_zero(tmp_path, monkeypatch):
    _install_tts(monkeypatch, tmp_path, ttl=0, max_bytes=0)
    keeper = tmp_path / "tts_keep.mp3"
    keeper.write_bytes(b"y" * 10_000)
    old = time.time() - 10_000_000
    os.utime(keeper, (old, old))

    assert rag_pipeline.prune_audio_cache() == 0
    assert keeper.exists()


def test_reuse_refreshes_recency_so_popular_answers_survive(tmp_path, monkeypatch):
    _install_tts(monkeypatch, tmp_path, ttl=0, max_bytes=10_000)
    with app_module.app.test_request_context("/"):
        url = rag_pipeline.text_to_speech_to_static("Conseil populaire.")
    path = tmp_path / Path(url).name
    old = time.time() - 5000
    os.utime(path, (old, old))
    before = path.stat().st_mtime

    with app_module.app.test_request_context("/"):
        rag_pipeline.text_to_speech_to_static("Conseil populaire.")

    assert path.stat().st_mtime > before


def test_failed_synthesis_leaves_no_partial_file(tmp_path, monkeypatch):
    class FailingGTTS:
        def __init__(self, text, lang, timeout):
            pass

        def save(self, output_path):
            Path(output_path).write_bytes(b"partial")
            raise TimeoutError("gTTS took too long")

    monkeypatch.setattr(rag_pipeline.gtts, "gTTS", FailingGTTS)
    monkeypatch.setattr(rag_pipeline, "AUDIO_OUTPUT_DIR", str(tmp_path))

    with app_module.app.test_request_context("/"):
        assert rag_pipeline.text_to_speech_to_static("Conseil.") == ""

    # No half-written file is reachable under the deterministic name.
    assert list(tmp_path.glob("*.mp3")) == []
    assert list(tmp_path.glob(".tts-*")) == []


def test_corrupt_zero_byte_file_is_regenerated(tmp_path, monkeypatch):
    _install_tts(monkeypatch, tmp_path)
    text = "Conseil à revoicer."
    (tmp_path / rag_pipeline._speech_filename(text)).write_bytes(b"")

    with app_module.app.test_request_context("/"):
        url = rag_pipeline.text_to_speech_to_static(text)

    assert url
    assert _CountingGTTS.calls == 1
    assert (tmp_path / Path(url).name).stat().st_size > 0


def test_abandoned_partial_is_removed_but_recent_and_unrelated_files_survive(tmp_path, monkeypatch):
    _install_tts(monkeypatch, tmp_path)
    stale = tmp_path / '.tts-abandoned.part'
    fresh = tmp_path / '.tts-active.part'
    unrelated = tmp_path / 'notes.part'
    for path in (stale, fresh, unrelated):
        path.write_bytes(b'partial')
    os.utime(stale, (1, 1))
    os.utime(unrelated, (1, 1))
    rag_pipeline.prune_audio_cache()
    assert not stale.exists()
    assert fresh.read_bytes() == b'partial'
    assert unrelated.read_bytes() == b'partial'


def test_audio_cleanup_does_not_follow_symlinks(tmp_path, monkeypatch):
    audio = tmp_path / 'audio'
    audio.mkdir()
    _install_tts(monkeypatch, audio, ttl=1)
    external = tmp_path / 'private.mp3'
    external.write_bytes(b'private')
    os.utime(external, (1, 1))
    link = audio / 'linked.mp3'
    link.symlink_to(external)
    rag_pipeline.prune_audio_cache()
    assert external.read_bytes() == b'private'
    assert link.is_symlink()


def test_cleanup_preserves_an_old_partial_while_synthesis_is_running(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    started, resume = Event(), Event()
    _install_tts(monkeypatch, tmp_path)

    class PausedGTTS:
        def __init__(self, **kwargs):
            pass

        def save(self, output_path):
            Path(output_path).write_bytes(b'partial')
            os.utime(output_path, (1, 1))
            started.set()
            assert resume.wait(5)
            assert Path(output_path).exists()
            Path(output_path).write_bytes(b'complete mp3')

    monkeypatch.setattr(rag_pipeline.gtts, 'gTTS', PausedGTTS)

    def generate():
        with app_module.app.test_request_context('/'):
            return rag_pipeline.text_to_speech_to_static('Conseil en cours.')

    with ThreadPoolExecutor(max_workers=1) as pool:
        result = pool.submit(generate)
        try:
            assert started.wait(5)
            rag_pipeline.prune_audio_cache()
            assert len(list(tmp_path.glob('.tts-*.part'))) == 1
        finally:
            resume.set()
        url = result.result(timeout=5)
    assert (tmp_path / Path(url).name).read_bytes() == b'complete mp3'
    assert not list(tmp_path.glob('.tts-*.part'))


def test_concurrent_same_answer_publishes_only_complete_audio(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    ready = Barrier(4)
    _install_tts(monkeypatch, tmp_path)

    class ConcurrentGTTS:
        def __init__(self, **kwargs):
            pass

        def save(self, output_path):
            Path(output_path).write_bytes(b'partial')
            ready.wait(timeout=5)
            assert not list(tmp_path.glob('*.mp3')) or all(
                p.read_bytes() == b'complete audio' for p in tmp_path.glob('*.mp3'))
            Path(output_path).write_bytes(b'complete audio')

    monkeypatch.setattr(rag_pipeline.gtts, 'gTTS', ConcurrentGTTS)

    def generate(_):
        with app_module.app.test_request_context('/'):
            return rag_pipeline.text_to_speech_to_static('Même conseil.')

    with ThreadPoolExecutor(max_workers=4) as workers:
        urls = list(workers.map(generate, range(4)))
    assert len(set(urls)) == 1
    assert urls[0]
    assert list(tmp_path.glob('.tts-*.part')) == []
    assert len(list(tmp_path.glob('*.mp3'))) == 1
    assert (tmp_path / Path(urls[0]).name).read_bytes() == b'complete audio'


def test_concurrent_distinct_answers_converge_to_audio_budget(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    _install_tts(monkeypatch, tmp_path, ttl=0, max_bytes=100)

    def generate(index):
        with app_module.app.test_request_context('/'):
            return rag_pipeline.text_to_speech_to_static('Conseil synthétique ' + str(index))

    with ThreadPoolExecutor(max_workers=4) as workers:
        urls = list(workers.map(generate, range(12)))
    assert all(urls)
    # Current responses may temporarily exceed the soft cap; a quiescent pass converges.
    rag_pipeline.prune_audio_cache()
    remaining = list(tmp_path.glob('*.mp3'))
    assert sum(path.stat().st_size for path in remaining) <= 100
    assert all(path.read_bytes().startswith(b'fake mp3 Conseil') for path in remaining)
    assert not list(tmp_path.glob('.tts-*.part'))
