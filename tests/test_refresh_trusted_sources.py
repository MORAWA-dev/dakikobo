"""Tests for offline trusted-source refresh wrapper."""

from pathlib import Path

from scripts.refresh_trusted_sources import main


def test_dry_run_lists_urls_and_skips_down(tmp_path, capsys, monkeypatch):
    seeds = tmp_path / "seeds.txt"
    seeds.write_text(
        "# comment\nhttps://www.agriculture.bf/\n\nhttps://wascal.org/\n",
        encoding="utf-8",
    )

    def fake_probe(url, timeout):
        ok = "wascal" not in url
        return {
            "url": url,
            "ok": ok,
            "status_code": 200 if ok else None,
            "error": "" if ok else "offline",
            "elapsed_ms": 1,
        }

    monkeypatch.setattr("scripts.refresh_trusted_sources.probe_url", fake_probe)
    code = main(["--urls-file", str(seeds), "--dry-run"])
    assert code == 0
    out = capsys.readouterr().out
    assert "https://www.agriculture.bf/" in out
    assert "https://wascal.org/" in out
    assert "DOWN" in out
    assert "Would skip 1 DOWN" in out
    assert "Dry run" in out


def test_dry_run_skip_health_check(tmp_path, capsys):
    seeds = tmp_path / "seeds.txt"
    seeds.write_text("https://example.org/\n", encoding="utf-8")
    code = main(["--urls-file", str(seeds), "--dry-run", "--skip-health-check"])
    assert code == 0
    out = capsys.readouterr().out
    assert "https://example.org/" in out
    assert "Preflight" not in out


def test_missing_seed_file_fails():
    code = main(["--urls-file", "/tmp/does-not-exist-seeds.txt", "--dry-run"])
    assert code == 2
