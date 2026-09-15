# Evaluation Reports

This directory holds generated DakiKobo evaluation reports.

Generate the public Space report with:

```bash
python scripts/evaluate_rag.py
```

The default output is:

```text
reports/rag_eval_results.md
```

Reports are snapshots of live app behavior. Regenerate them after RAG, source,
prompt, weather, soil, or deployment changes.


## Headless-browser rehearsal

`reports/browser_replay_check/` holds the automated Chromium rehearsal output.
Reproduce it from a fresh checkout (browser deps are test-only and never ship
in production):

```bash
pip install -r requirements-browser.txt
python -m playwright install --with-deps chromium
python tests/browser_replay_check.py --widths 320,1280
```

The runner starts `tests/browser_fixture_app.py` itself (synthetic, no provider
or model calls), waits for readiness with a deadline, checks keyboard
navigation, modal focus/Escape behaviour, 320 px overflow, and audio-failure
recovery, then tears the fixture down. Screenshots (`replay-*.png`),
`results.json`, and `fixture.log` are generated artifacts (git-ignored; CI
uploads them). CI runs this in `.github/workflows/browser-rehearsal.yml`.

This is **headless-browser evidence only** — not physical-phone testing and not
participant/farmer usability validation. The dated
`accessibility-2026-09-12.md` in that folder is human review evidence and is
kept under version control.
