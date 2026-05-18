# Phase 256 - Scale Smoke Pending Range Guard

## Goal

Extend the long-form scale smoke report so it proves range background tasks have
no pending chapters after the synthetic thousand-chapter run completes. This
keeps the new pending chapter helper covered by the million-word validation path.

## TDD Evidence

- RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_longform_scale.py -q -k "smoke_reports_memory_retrieval_and_resume_progress"`
  - Failed because the smoke task report did not include
    `pending_chapter_count`.
- GREEN:
  - Same focused command passed with `1 passed`.
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_longform_scale.py -q`
    passed with `43 passed`.

## Changes

- `run_longform_scale_smoke()` now calls
  `BackgroundTaskService.pending_chapter_indexes()` after completing the range
  task.
- Smoke task output includes:
  - `pending_chapter_count`
  - `next_pending_chapter_index`

## Verification Evidence

- `backend\.venv\Scripts\python.exe scripts\longform_scale_smoke.py --chapters 1000 --words-per-chapter 1000 --cleanup`
  exited 0 with `total_words=1000000`, `elapsed_ms=8570`,
  `retrieval_reindex=6682`, `retrieval_diagnostics=1004`,
  `retrieval_repeat_reindex=153`, `context_build=274`,
  `query_aware_retrieval_item_count=6`,
  `query_aware_retrieval_has_explanations=true`,
  `query_aware_retrieval_out_of_range_count=0`,
  `task.pending_chapter_count=0`,
  `task.next_pending_chapter_index=null`,
  `repeat_reindex.indexed.documents=0`, and
  `repeat_reindex.preserved_documents=2061`.
- `backend\.venv\Scripts\python.exe -m pytest backend/tests -q` passed with
  `650 passed in 55.88s`.
- `npm run build` passed.
- `npm run test:unit -- --run` passed with `62 passed` files and
  `418 passed` tests.
- `git diff --check` passed.
- DeepSeek key scan returned `NO_MATCH`.
