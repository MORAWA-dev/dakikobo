"""Tests for the headless-browser rehearsal's failure-evidence capture.

The unit test uses a fake page and needs no browser, so it runs in the normal
offline suite. The end-to-end test runs the real rehearsal with an injected
early failure and is skipped when Playwright/Chromium is unavailable.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import tests.browser_replay_check as rehearsal


class _FakePage:
    """Minimal page double: records screenshot calls, never touches a browser."""

    def __init__(self):
        self.screenshots = []

    def screenshot(self, path, full_page=False):
        Path(path).write_bytes(b"\x89PNG\r\n\x1a\n fake screenshot")
        self.screenshots.append(path)


def test_capture_failure_writes_screenshot_and_report_before_close(tmp_path):
    """On failure, a screenshot and structured error.json are written."""
    page = _FakePage()
    partial = [{"width": 320, "ok": True}]
    error = AssertionError("Injected deliberate failure at 1280px")

    try:
        raise error
    except AssertionError as raised:
        rehearsal._capture_failure(page, tmp_path, 1280, raised, partial)

    screenshot = tmp_path / "failure-1280.png"
    report_path = tmp_path / "error.json"
    assert screenshot.exists() and screenshot.stat().st_size > 0
    assert report_path.exists()

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["failed_width"] == 1280
    assert report["error_type"] == "AssertionError"
    assert "Injected deliberate failure" in report["error"]
    assert report["screenshot"] == "failure-1280.png"
    assert report["partial_results"] == partial
    assert "Traceback" in report["traceback"]


def _chromium_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return False
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            browser.close()
        return True
    except Exception:
        return False


@pytest.mark.skipif(
    not _chromium_available(),
    reason="Playwright Chromium not installed; run in the browser-rehearsal CI job.",
)
def test_injected_failure_run_produces_evidence(tmp_path):
    """An injected early assertion failure fails and leaves captured evidence."""
    root = Path(__file__).resolve().parents[1]
    env = dict(
        os.environ,
        BROWSER_REPLAY_INJECT_FAILURE="1",
        GROQ_API_KEY="ci-placeholder",
        RAG_WARMUP_ON_START="false",
    )
    run_id = "pytest-injected"
    result = subprocess.run(
        [
            sys.executable, "tests/browser_replay_check.py",
            "--widths", "320", "--port", "0", "--run-id", run_id,
        ],
        cwd=str(root), env=env, capture_output=True, text=True, timeout=180,
    )
    artifact_dir = root / "reports" / "browser_replay_check" / run_id
    try:
        assert result.returncode == 1, result.stderr
        assert (artifact_dir / "error.json").exists()
        assert (artifact_dir / "failure-320.png").exists()
        report = json.loads((artifact_dir / "error.json").read_text(encoding="utf-8"))
        assert "Injected deliberate failure" in report["error"]
    finally:
        shutil.rmtree(artifact_dir, ignore_errors=True)
