"""Headless browser check for expired audio recovery at mobile and desktop widths."""

import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


OUTPUT = Path("reports/browser_replay_check")
OUTPUT.mkdir(parents=True, exist_ok=True)


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    results = []
    for width in (320, 1280):
        context = browser.new_context(
            viewport={"width": width, "height": 900},
            service_workers="block",
        )
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto("http://127.0.0.1:5097")
        page.wait_for_load_state("networkidle")

        page.keyboard.press("Tab")
        expect(page.locator(".skip-link")).to_be_focused()
        page.keyboard.press("Enter")
        expect(page.locator("#mainContent")).to_be_focused()

        page.locator("#credibilityToggle").focus()
        page.keyboard.press("Enter")
        expect(page.locator("#credibilityClose")).to_be_focused()
        page.keyboard.press("Tab")
        expect(page.locator("#credibilityClose")).to_be_focused()
        page.keyboard.press("Escape")
        expect(page.locator("#credibilityToggle")).to_be_focused()

        page.locator("#journalToggle").focus()
        page.keyboard.press("Enter")
        expect(page.locator("#journalClose")).to_be_focused()
        page.locator("#clearDeviceData").focus()
        page.keyboard.press("Tab")
        expect(page.locator("#journalClose")).to_be_focused()
        page.keyboard.press("Escape")
        expect(page.locator("#journalToggle")).to_be_focused()

        page.locator("#messageText").fill("Mon mil")
        page.locator("#chatbot-form-btn").click()
        replay = page.get_by_role("button", name="Réécouter la réponse").last
        expect(replay).to_be_visible()
        replay.click()
        status = page.locator(".audio-status").filter(has_text="indisponible")
        expect(status).to_be_visible()
        expect(page.locator(".chat-messages")).to_contain_text(
            "Conseil synthétique : le texte reste disponible."
        )
        overflow = page.evaluate(
            "document.documentElement.scrollWidth > window.innerWidth"
        )
        assert not overflow, f"Horizontal overflow at {width}px"
        assert not errors, errors
        page.screenshot(path=str(OUTPUT / f"replay-{width}.png"), full_page=True)
        results.append(
            {
                "width": width,
                "replay_error_visible": True,
                "text_preserved": True,
                "horizontal_overflow": overflow,
                "page_errors": errors,
                "skip_link": True,
                "dialog_focus_contained": True,
                "escape_restores_focus": True,
            }
        )
        context.close()
    browser.close()

(OUTPUT / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
