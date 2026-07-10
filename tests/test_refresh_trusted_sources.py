"""Tests for offline trusted-source refresh wrapper."""

from pathlib import Path

from scripts.refresh_trusted_sources import main


def test_dry_run_lists_urls(tmp_path, capsys):
    seeds = tmp_path / "seeds.txt"
    seeds.write_text(
        "# comment\nhttps://www.agriculture.bf/\n\nhttps://wascal.org/\n",
        encoding="utf-8",
    )
    code = main(["--urls-file", str(seeds), "--dry-run"])
    assert code == 0
    out = capsys.readouterr().out
    assert "https://www.agriculture.bf/" in out
    assert "https://wascal.org/" in out
    assert "Dry run" in out


def test_missing_seed_file_fails():
    code = main(["--urls-file", "/tmp/does-not-exist-seeds.txt", "--dry-run"])
    assert code == 2
