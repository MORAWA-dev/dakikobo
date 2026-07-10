"""Tests for trusted-source HTTP health probes."""

from scripts.check_trusted_sources import format_markdown, main, probe_url, read_urls


def test_read_urls_skips_comments(tmp_path):
    seed = tmp_path / "seeds.txt"
    seed.write_text(
        "# comment\nhttps://example.org/\n\nhttps://example.com/\n",
        encoding="utf-8",
    )
    assert read_urls(seed) == ["https://example.org/", "https://example.com/"]


def test_probe_url_ok(monkeypatch):
    class FakeResponse:
        status_code = 200

    def fake_head(url, timeout, allow_redirects):
        return FakeResponse()

    monkeypatch.setattr("scripts.check_trusted_sources.requests.head", fake_head)
    result = probe_url("https://example.org/", timeout=5.0)
    assert result["ok"] is True
    assert result["status_code"] == 200


def test_probe_url_error(monkeypatch):
    import requests

    def boom(*args, **kwargs):
        raise requests.ConnectionError("offline")

    monkeypatch.setattr("scripts.check_trusted_sources.requests.head", boom)
    result = probe_url("https://down.example/", timeout=1.0)
    assert result["ok"] is False
    assert "offline" in result["error"]


def test_format_markdown_and_main_dry(tmp_path, monkeypatch, capsys):
    seed = tmp_path / "seeds.txt"
    seed.write_text("https://ok.example/\nhttps://bad.example/\n", encoding="utf-8")
    log = tmp_path / "health.md"

    def fake_probe(url, timeout):
        return {
            "url": url,
            "ok": url.startswith("https://ok"),
            "status_code": 200 if url.startswith("https://ok") else None,
            "error": "" if url.startswith("https://ok") else "down",
            "elapsed_ms": 10,
        }

    monkeypatch.setattr("scripts.check_trusted_sources.probe_url", fake_probe)
    code = main(["--urls-file", str(seed), "--log", str(log)])
    assert code == 0
    out = capsys.readouterr().out
    assert "UP" in out and "DOWN" in out
    text = log.read_text(encoding="utf-8")
    assert "Trusted source health" in text
    assert "1/2" in text
    md = format_markdown(
        [
            {
                "url": "https://ok.example/",
                "ok": True,
                "status_code": 200,
                "error": "",
                "elapsed_ms": 1,
            }
        ],
        started="t",
    )
    assert "UP" in md
