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
failure exits non-zero so CI fails. Screenshots and a results.json are written
under ``reports/browser_replay_check`` for CI failure artifacts; they are not
committed.

Usage (from a fresh checkout, browser deps installed separately):

    python -m playwright install chromium
    python tests/browser_replay_check.py

Optional flags / env:
  --port N                 fixture port (default 5097; 0 lets the OS choose)
  --startup-timeout S      seconds to wait for fixture readiness (default 30)
  --widths 320,1280        comma-separated viewport widths
  BROWSER_REPLAY_INJECT_FAILURE=1
                           inject a deliberate false assertion to prove the
                           rehearsal detects failures (used only in CI's
                           failure-detection step; never left enabled).
"""

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from contextlib import closing, contextmanager
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "browser_fixture_app.py"
OUTPUT = ROOT / "reports" / "browser_replay_check"

INJECT_FAILURE = os.environ.get("BROWSER_REPLAY_INJECT_FAILURE") == "1"


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@contextmanager
def fixture_server(port: int, startup_timeout: float):
    """Start the synthetic fixture app and guarantee teardown.

    Raises TimeoutError if the app does not answer /healthz before the
    deadline. The process is always terminated (then killed) on exit.
    """
    log_path = OUTPUT / "fixture.log"
    OUTPUT.mkdir(parents=True, exist_ok=True)
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
            base_url = f"http://127.0.0.1:{port}"
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
            yield base_url
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def _open_dialog_via_keyboard(page, toggle: str, close: str) -> None:
    """Activate a dialog opener from the keyboard and confirm focus moved in.

    Enter on a focused button dispatches the same click handler that opens the
    dialog. In headless Chromium the tab occasionally needs re-activation before
    the synthesized key lands, so this retries the keyboard activation a few
    times before asserting, rather than racing the dialog's own focus() call.
    """
    for _ in range(5):
        page.bring_to_front()
        page.locator(toggle).focus()
        page.keyboard.press("Enter")
        try:
            expect(page.locator(close)).to_be_focused(timeout=2000)
            return
        except (AssertionError, PlaywrightError):
            # Close it if it opened but focus did not settle, then retry.
            page.keyboard.press("Escape")
    # Final attempt surfaces the real assertion error to the caller.
    page.bring_to_front()
    page.locator(toggle).focus()
    page.keyboard.press("Enter")
    expect(page.locator(close)).to_be_focused()


def _assert_focus_trapped(page, dialog_selector: str, tabs: int = 4) -> None:
    """Tab several times and confirm focus never escapes the open dialog.

    The credibility dialog contains more than one focusable control (close
    button + privacy link), so the trap cycles focus between them rather than
    pinning it on a single element. Containment is the real accessibility
    contract, so we assert focus stays inside the dialog across Tabs.
    """
    for _ in range(tabs):
        page.keyboard.press("Tab")
        inside = page.evaluate(
            "(sel) => document.querySelector(sel).contains(document.activeElement)",
            dialog_selector,
        )
        assert inside, f"Focus escaped {dialog_selector} while tabbing"


def _run_width(page, width: int) -> dict:
    """Run every acceptance check at one viewport width."""
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    # Bring the tab to the foreground so :focus assertions are reliable in
    # headless Chromium.
    page.bring_to_front()

    # Keyboard navigation: skip link -> main landmark.
    page.keyboard.press("Tab")
    expect(page.locator(".skip-link")).to_be_focused()
    page.keyboard.press("Enter")
    expect(page.locator("#mainContent")).to_be_focused()

    # Credibility modal: open, focus lands on close, focus stays trapped inside
    # while tabbing, and Escape restores focus to the opener.
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
    # Full Chromium raises the media 'error' from the undecodable payload on its
    # own; the headless *shell* available in some environments has no media
    # pipeline and may not, so if the recovery message has not appeared shortly
    # we emit the same 'error' on the element the app created (captured by the
    # context init script). Either way the app's genuine onFailure handler runs.
    page.locator("#messageText").fill("Mon mil")
    page.locator("#chatbot-form-btn").click()
    replay = page.get_by_role("button", name="Réécouter la réponse").last
    expect(replay).to_be_visible()
    status = page.locator(".audio-status").filter(has_text="indisponible")
    # Activate replay until the app has actually constructed an Audio for the
    # broken source (captured by the context init script). The button toggles
    # play/pause, so on a headless click race we click again; an odd click
    # count lands on "play".
    for _ in range(6):
        replay.click()
        try:
            page.wait_for_function(
                "() => (window.__dakikoboAudios || []).length > 0", timeout=2000
            )
            break
        except PlaywrightError:
            continue
    # Full Chromium raises the media 'error' on its own; a headless build with
    # no media pipeline may not, so emit the same 'error' the browser would on
    # the element the app created. Either path runs the app's real onFailure.
    try:
        expect(status).to_be_visible(timeout=4000)
    except AssertionError:
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
    # regressions. Never enabled outside the dedicated failure-detection step.
    assert not INJECT_FAILURE, f"Injected deliberate failure at {width}px"
    assert not errors, errors

    page.screenshot(path=str(OUTPUT / f"replay-{width}.png"), full_page=True)
    return {
        "width": width,
        "replay_error_visible": True,
        "text_preserved": True,
        "horizontal_overflow": overflow,
        "page_errors": errors,
        "skip_link": True,
        "dialog_focus_contained": True,
        "escape_restores_focus": True,
    }


def run(base_url: str, widths: list[int]) -> list[dict]:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            for width in widths:
                context = browser.new_context(
                    viewport={"width": width, "height": 900},
                    service_workers="block",
                )
                # Capture the Audio elements the app creates so the audio-failure
                # check can drive a real media 'error' deterministically even on
                # a headless build without a media pipeline.
                context.add_init_script(
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
                try:
                    page = context.new_page()
                    page.goto(base_url)
                    page.wait_for_load_state("networkidle")
                    results.append(_run_width(page, width))
                finally:
                    context.close()
        finally:
            browser.close()
    (OUTPUT / "results.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=5097)
    parser.add_argument("--startup-timeout", type=float, default=30.0)
    parser.add_argument("--widths", default="320,1280")
    args = parser.parse_args()

    widths = [int(value) for value in args.widths.split(",") if value.strip()]
    port = _free_port() if args.port == 0 else args.port

    try:
        with fixture_server(port, args.startup_timeout) as base_url:
            results = run(base_url, widths)
    except (AssertionError, PlaywrightError, TimeoutError, RuntimeError) as error:
        print(f"Browser rehearsal FAILED: {error}", file=sys.stderr)
        return 1

    print("Browser rehearsal passed (headless-browser evidence only):")
    for result in results:
        print(f"  - {result['width']}px: no overflow, no page errors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
