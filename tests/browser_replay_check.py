"""Automated headless-browser rehearsal for the DakiKobo frontend.

This is HEADLESS-BROWSER evidence only. It is NOT physical-phone testing and
NOT participant/farmer usability validation. It exercises, at 320 px and
1280 px, against an isolated synthetic Flask fixture that never calls a model
or an external provider:

  * keyboard navigation (skip link -> main landmark),
  * modal focus containment and Escape restoration (credibility + journal),
  * absence of horizontal overflow (mobile fit),
  * audio-failure recovery (expired/missing audio keeps the text answer).

The runner owns the whole lifecycle: it starts ``tests/browser_fixture_app.py``,
waits for readiness with a hard deadline, runs the checks, and always tears the
fixture process down, even when an assertion, startup, or timeout fails. Any
failure exits non-zero so CI fails.

Artifacts (screenshots, ``results.json``, ``error.json``, ``fixture.log``) are
written under ``reports/browser_replay_check/<run-id>/``. Each invocation gets
its own run directory so the deliberate failure-detection runs never overwrite
or reuse a normal run's evidence. When an assertion fails, a screenshot and a
structured ``error.json`` are captured BEFORE the browser context is closed, so
the failing state is preserved. Artifacts are not committed.

Usage (from a fresh checkout, browser deps installed separately):

    python -m playwright install chromium
    python tests/browser_replay_check.py

Optional flags / env:
  --port N                 fixture port (default 5097; 0 lets the OS choose)
  --startup-timeout S      seconds to wait for fixture readiness (default 30)
  --widths 320,1280        comma-separated viewport widths
  --run-id NAME            artifact subdirectory name (default: timestamped)
  BROWSER_REPLAY_RUN_ID    same as --run-id (env form, for CI steps)
  BROWSER_REPLAY_INJECT_FAILURE=1
                           inject a deliberate false assertion to prove the
                           rehearsal detects failures and captures evidence
                           (used only in CI's failure-detection step).
"""

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import traceback
from contextlib import closing, contextmanager
from pathlib import Path

# Playwright is a TEST-ONLY dependency (requirements-browser.txt) and is not
# installed in the offline regression job. Import it lazily so this module can
# be imported (e.g. by the unit test for the failure-capture helper) without
# Playwright present. ``_load_playwright`` populates the module globals used by
# the browser-driving functions and raises a clear error if it is missing.
expect = None  # type: ignore[assignment]
sync_playwright = None  # type: ignore[assignment]


class PlaywrightError(Exception):
    """Placeholder until the real Playwright error type is loaded."""


def _load_playwright() -> None:
    """Bind the real Playwright symbols into module globals (lazy import)."""
    global expect, sync_playwright, PlaywrightError
    from playwright.sync_api import Error as _PlaywrightError
    from playwright.sync_api import expect as _expect
    from playwright.sync_api import sync_playwright as _sync_playwright

    expect = _expect
    sync_playwright = _sync_playwright
    PlaywrightError = _PlaywrightError


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "browser_fixture_app.py"
ARTIFACT_ROOT = ROOT / "reports" / "browser_replay_check"

INJECT_FAILURE = os.environ.get("BROWSER_REPLAY_INJECT_FAILURE") == "1"

# The Audio-capture init script lets the audio-failure check drive a real media
# 'error' deterministically even on a headless build with no media pipeline.
_AUDIO_CAPTURE_SCRIPT = (
    "(function () {"
    "  var Original = window.Audio;"
    "  window.__dakikoboAudios = [];"
    "  window.Audio = function (src) {"
    "    var element = new Original(src);"
    "    window.__dakikoboAudios.push(element);"
    "    return element;"
    "  };"
    "  window.Audio.prototype = Original.prototype;"
    "})();"
)


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def default_run_id() -> str:
    """A unique-per-invocation artifact directory name."""
    explicit = os.environ.get("BROWSER_REPLAY_RUN_ID", "").strip()
    if explicit:
        return explicit
    return f"run-{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}"


@contextmanager
def fixture_server(port: int, startup_timeout: float, artifact_dir: Path):
    """Start the synthetic fixture app and guarantee teardown.

    Raises TimeoutError if the app does not answer before the deadline. The
    process is always terminated (then killed) on exit.
    """
    artifact_dir.mkdir(parents=True, exist_ok=True)
    log_path = artifact_dir / "fixture.log"
    env = dict(os.environ, BROWSER_FIXTURE_PORT=str(port))
    with log_path.open("w+", encoding="utf-8") as log:
        process = subprocess.Popen(
            [sys.executable, str(FIXTURE)],
            cwd=str(ROOT),
            env=env,
            stdout=log,
            stderr=log,
        )
        try:
            deadline = time.monotonic() + startup_timeout
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    log.seek(0)
                    raise RuntimeError(
                        "Fixture process exited during startup:\n" + log.read()
                    )
                try:
                    with closing(socket.create_connection(("127.0.0.1", port), 0.5)):
                        break
                except OSError:
                    time.sleep(0.1)
            else:
                log.seek(0)
                raise TimeoutError(
                    f"Fixture did not become ready within {startup_timeout}s:\n"
                    + log.read()
                )
            yield f"http://127.0.0.1:{port}"
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def _open_dialog_via_keyboard(page, toggle: str, close: str) -> None:
    """Activate a dialog opener from the keyboard and confirm focus moved in."""
    for _ in range(5):
        page.bring_to_front()
        page.locator(toggle).focus()
        page.keyboard.press("Enter")
        try:
            expect(page.locator(close)).to_be_focused(timeout=2000)
            return
        except (AssertionError, PlaywrightError):
            page.keyboard.press("Escape")
    page.bring_to_front()
    page.locator(toggle).focus()
    page.keyboard.press("Enter")
    expect(page.locator(close)).to_be_focused()


def _assert_focus_trapped(page, dialog_selector: str, tabs: int = 4) -> None:
    """Tab several times and confirm focus never escapes the open dialog."""
    for _ in range(tabs):
        page.keyboard.press("Tab")
        inside = page.evaluate(
            "(sel) => document.querySelector(sel).contains(document.activeElement)",
            dialog_selector,
        )
        assert inside, f"Focus escaped {dialog_selector} while tabbing"


def _run_width(page, width: int) -> dict:
    """Run every acceptance check at one viewport width.

    Returns a result dict including how the audio failure was produced:
    ``audio_failure_mode`` is ``"native"`` when the browser raised the media
    error on its own, or ``"synthetic-error-event"`` when this runner emitted
    the media 'error' the browser would (headless build without a media
    pipeline). Both paths drive the app's genuine recovery handler.
    """
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.bring_to_front()

    # Keyboard navigation: skip link -> main landmark.
    page.keyboard.press("Tab")
    expect(page.locator(".skip-link")).to_be_focused()
    page.keyboard.press("Enter")
    expect(page.locator("#mainContent")).to_be_focused()

    # Credibility modal: open, focus lands on close, stays trapped, Escape restores.
    _open_dialog_via_keyboard(page, "#credibilityToggle", "#credibilityClose")
    _assert_focus_trapped(page, "#credibilityModal")
    page.keyboard.press("Escape")
    expect(page.locator("#credibilityToggle")).to_be_focused()

    # Private-journal dialog: same focus/escape contract.
    _open_dialog_via_keyboard(page, "#journalToggle", "#journalClose")
    _assert_focus_trapped(page, "#journalPanel")
    page.keyboard.press("Escape")
    expect(page.locator("#journalToggle")).to_be_focused()

    # Audio-failure recovery: expired/missing audio must not lose the answer.
    page.locator("#messageText").fill("Mon mil")
    page.locator("#chatbot-form-btn").click()
    replay = page.get_by_role("button", name="Réécouter la réponse").last
    expect(replay).to_be_visible()
    status = page.locator(".audio-status").filter(has_text="indisponible")
    # Activate replay until the app has constructed an Audio for the broken
    # source. The button toggles play/pause, so on a headless click race we
    # click again; an odd click count lands on "play".
    for _ in range(6):
        replay.click()
        try:
            page.wait_for_function(
                "() => (window.__dakikoboAudios || []).length > 0", timeout=2000
            )
            break
        except PlaywrightError:
            continue
    # Full Chromium raises the media 'error' natively; a headless build with no
    # media pipeline may not, so fall back to emitting the same 'error' event on
    # the element the app created. Record which path produced the failure.
    audio_failure_mode = "native"
    try:
        expect(status).to_be_visible(timeout=4000)
    except AssertionError:
        audio_failure_mode = "synthetic-error-event"
        page.evaluate(
            "(window.__dakikoboAudios || []).forEach("
            "el => el.dispatchEvent(new Event('error')))"
        )
        expect(status).to_be_visible(timeout=8000)
    # The text answer must survive the audio failure.
    expect(page.locator(".chat-messages")).to_contain_text(
        "Conseil synthétique : le texte reste disponible."
    )

    overflow = page.evaluate(
        "document.documentElement.scrollWidth > window.innerWidth"
    )
    assert not overflow, f"Horizontal overflow at {width}px"
    # A deliberate, opt-in failure so CI can prove the rehearsal detects
    # regressions AND captures evidence. Never enabled outside CI's dedicated
    # failure-detection step.
    assert not INJECT_FAILURE, f"Injected deliberate failure at {width}px"
    assert not errors, errors

    return {
        "width": width,
        "replay_error_visible": True,
        "text_preserved": True,
        "horizontal_overflow": overflow,
        "page_errors": errors,
        "skip_link": True,
        "dialog_focus_contained": True,
        "escape_restores_focus": True,
        "audio_failure_mode": audio_failure_mode,
    }


def _capture_failure(page, artifact_dir: Path, width: int, error: BaseException,
                     partial_results: list[dict]) -> None:
    """Save a screenshot and structured error report before the context closes."""
    screenshot = artifact_dir / f"failure-{width}.png"
    try:
        page.screenshot(path=str(screenshot), full_page=True)
        screenshot_saved = screenshot.name
    except Exception as shot_error:  # never mask the original failure
        screenshot_saved = f"screenshot-failed: {shot_error}"
    report = {
        "failed_width": width,
        "error_type": type(error).__name__,
        "error": str(error),
        "traceback": traceback.format_exc(),
        "screenshot": screenshot_saved,
        "partial_results": partial_results,
    }
    (artifact_dir / "error.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def run(base_url: str, widths: list[int], artifact_dir: Path) -> list[dict]:
    """Run the checks at each width; on failure capture evidence, then re-raise."""
    _load_playwright()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            for width in widths:
                context = browser.new_context(
                    viewport={"width": width, "height": 900},
                    service_workers="block",
                )
                context.add_init_script(_AUDIO_CAPTURE_SCRIPT)
                page = context.new_page()
                try:
                    page.goto(base_url)
                    page.wait_for_load_state("networkidle")
                    result = _run_width(page, width)
                    result["screenshot"] = f"replay-{width}.png"
                    page.screenshot(
                        path=str(artifact_dir / f"replay-{width}.png"),
                        full_page=True,
                    )
                    results.append(result)
                except BaseException as error:
                    # Capture the failing state BEFORE the context is torn down.
                    _capture_failure(page, artifact_dir, width, error, results)
                    raise
                finally:
                    context.close()
        finally:
            browser.close()
    (artifact_dir / "results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return results


def rehearse(port: int, widths: list[int], startup_timeout: float,
             artifact_dir: Path) -> list[dict]:
    """Full lifecycle: start fixture, run checks, always tear the fixture down."""
    with fixture_server(port, startup_timeout, artifact_dir) as base_url:
        return run(base_url, widths, artifact_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=5097)
    parser.add_argument("--startup-timeout", type=float, default=30.0)
    parser.add_argument("--widths", default="320,1280")
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()

    widths = [int(value) for value in args.widths.split(",") if value.strip()]
    port = _free_port() if args.port == 0 else args.port
    run_id = args.run_id or default_run_id()
    artifact_dir = ARTIFACT_ROOT / run_id

    try:
        results = rehearse(port, widths, args.startup_timeout, artifact_dir)
    except (AssertionError, PlaywrightError, TimeoutError, RuntimeError) as error:
        print(f"Browser rehearsal FAILED: {error}", file=sys.stderr)
        print(f"Evidence written under: {artifact_dir}", file=sys.stderr)
        return 1

    print("Browser rehearsal passed (headless-browser evidence only):")
    for result in results:
        print(
            f"  - {result['width']}px: no overflow, no page errors, "
            f"audio failure via {result['audio_failure_mode']}"
        )
    print(f"Artifacts: {artifact_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
