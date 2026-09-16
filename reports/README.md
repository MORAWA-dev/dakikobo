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
recovery, then tears the fixture down. Each invocation writes to its own
per-run subdirectory `reports/browser_replay_check/<run-id>/` (pass `--run-id`
or set `BROWSER_REPLAY_RUN_ID`), so the deliberate failure-detection runs never
overwrite a normal run's evidence. On a failed assertion, the runner captures a
screenshot (`failure-<width>.png`) and a structured `error.json` (error, full
traceback, partial results) **before** the browser context closes. A passing
run writes `replay-<width>.png` and `results.json`; `results.json` records
`audio_failure_mode` (`native` when the browser raised the media error itself,
`synthetic-error-event` when the runner emitted it for a headless build with no
media pipeline). All of these are generated artifacts (git-ignored; CI uploads
the whole tree on every run). CI runs this in
`.github/workflows/browser-rehearsal.yml`.

This is **headless-browser evidence only** — not physical-phone testing and not
participant/farmer usability validation. The dated
`accessibility-2026-09-12.md` in that folder is human review evidence and is
kept under version control.
