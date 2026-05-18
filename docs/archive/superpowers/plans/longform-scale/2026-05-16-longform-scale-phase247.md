# Phase 247 - Smoke Guard for Idempotent Retrieval Reindex

## Goal

Long-form maintenance should not turn every routine reindex into a full rewrite.
The scale smoke now validates the idempotent path by running a second retrieval
reindex after diagnostics and reporting whether unchanged documents were
preserved.

## TDD Evidence

- RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_longform_scale.py -q -k "memory_retrieval_and_resume_progress or reports_stage_timings"`
  - Failed because `repeat_reindex` and `retrieval_repeat_reindex` were missing.
- GREEN:
  - Same focused command passed with `2 passed`.
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_longform_scale.py -q`
    passed with `41 passed`.

## Changes

- Added a second `reindex_project_retrieval` run inside the long-form scale smoke.
- Added `repeat_reindex` to the smoke report and stored task result.
- Added `retrieval_repeat_reindex` to `timings_ms`.
- Test coverage now asserts repeated reindex writes zero documents, removes zero
  documents, and preserves the current retrieval document count.

## Scale Smoke

- Command:
  - `backend\.venv\Scripts\python.exe scripts\longform_scale_smoke.py --chapters 1000 --words-per-chapter 1000 --cleanup`
- Result:
  - `total_words`: 1,000,000
  - `elapsed_ms`: 8,568
  - `retrieval_reindex`: 6,714 ms
  - `retrieval_diagnostics`: 982 ms
  - `retrieval_repeat_reindex`: 141 ms
  - `repeat_reindex.indexed.documents`: 0
  - `repeat_reindex.preserved_documents`: 2,061
  - `repeat_reindex.removed_documents`: 0

## Verification

Full verification is required before committing this phase:

- `backend\.venv\Scripts\python.exe -m pytest backend/tests -q`
- `npm run build`
- `npm run test:unit -- --run`
- `git diff --check`
- DeepSeek key scan must return `NO_MATCH`.
