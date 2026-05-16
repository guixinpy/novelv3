# Phase 248 - Fail Smoke on Non-Idempotent Repeat Reindex

## Goal

Make the scale smoke fail when the second retrieval reindex rewrites unchanged
documents. This turns the repeat reindex metric into an automated guard instead
of leaving the regression hidden in JSON output.

## TDD Evidence

- RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_longform_scale.py -q -k "repeat_reindex_writes_documents"`
  - Failed because the CLI returned `0` when the fake repeat reindex indexed one
    document.
- GREEN:
  - Same focused command passed with `1 passed`.
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_longform_scale.py -q`
    passed with `42 passed`.

## Changes

- Extended `_threshold_failures` to validate `repeat_reindex` when present.
- The CLI now fails if repeat reindex:
  - indexes any documents,
  - removes any documents,
  - or preserves fewer documents than the retrieval diagnostic total.

## Scale Smoke

- Command:
  - `backend\.venv\Scripts\python.exe scripts\longform_scale_smoke.py --chapters 1000 --words-per-chapter 1000 --cleanup`
- Result:
  - `total_words`: 1,000,000
  - `elapsed_ms`: 8,520
  - `retrieval_reindex`: 6,647 ms
  - `retrieval_diagnostics`: 978 ms
  - `retrieval_repeat_reindex`: 142 ms
  - `repeat_reindex.indexed.documents`: 0
  - `repeat_reindex.preserved_documents`: 2,061
  - CLI exit code: 0

## Verification

Full verification is required before committing this phase:

- `backend\.venv\Scripts\python.exe -m pytest backend/tests -q`
- `npm run build`
- `npm run test:unit -- --run`
- `git diff --check`
- DeepSeek key scan must return `NO_MATCH`.
