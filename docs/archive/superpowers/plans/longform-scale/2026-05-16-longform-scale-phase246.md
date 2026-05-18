# Phase 246 - Split Retrieval Smoke Timing

## Goal

Make the long-form scale smoke report separate retrieval index rebuild time from
post-rebuild diagnostic counting. The previous `retrieval_reindex` stage included
both operations, which made the true indexing bottleneck harder to evaluate.

## TDD Evidence

- RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_longform_scale.py -q -k "reports_stage_timings"`
  - Failed because `retrieval_diagnostics` was missing from `timings_ms`.
- GREEN:
  - Same focused command passed with `1 passed`.
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_longform_scale.py -q`
    passed with `41 passed`.

## Changes

- Recorded `retrieval_reindex` immediately after `reindex_project_retrieval`.
- Added a separate `retrieval_diagnostics` timing around `get_retrieval_diagnostics`.
- Kept the smoke report payload shape stable; only `timings_ms` gained the new
  stage key.

## Scale Smoke

- Command:
  - `backend\.venv\Scripts\python.exe scripts\longform_scale_smoke.py --chapters 1000 --words-per-chapter 1000 --cleanup`
- Result:
  - `total_words`: 1,000,000
  - `elapsed_ms`: 8,532
  - `retrieval_reindex`: 6,777 ms
  - `retrieval_diagnostics`: 970 ms
  - `total_documents`: 2,061
  - `total_chunks`: 3,061
  - `total_terms`: 249,022

## Verification

Full verification is required before committing this phase:

- `backend\.venv\Scripts\python.exe -m pytest backend/tests -q`
- `npm run build`
- `npm run test:unit -- --run`
- `git diff --check`
- DeepSeek key scan must return `NO_MATCH`.
