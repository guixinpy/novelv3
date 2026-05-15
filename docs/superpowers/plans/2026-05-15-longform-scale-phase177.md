# Phase 177 - Keep Longform Memory Diagnostics Read-Only

## Problem

`get_longform_memory_diagnostics` recalculated chapter word totals and could write the
result back to `Project.current_word_count` during a diagnostics read. On large
projects this adds an avoidable aggregate scan to a UI health check and gives a GET
style diagnostic path write side effects.

## Change

- Removed word-count reconciliation from the longform memory diagnostics read path.
- Diagnostics now reports the maintained `Project.current_word_count`.
- Existing rebuild and repair/write paths still reconcile or maintain project word
  count where they mutate longform state.

## Tests

- RED: `backend/tests/test_longform_scale.py::test_longform_memory_diagnostics_chapter_count_does_not_select_chapter_content`
- GREEN: target diagnostics read-only test
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
- GREEN: `npm run test:unit` from `frontend`
- GREEN: `npm run build` from `frontend`
- GREEN: `git diff --check`
- GREEN: DeepSeek key scan returned `NO_MATCH`

## Result

Longform memory diagnostics no longer performs a full chapter word-count aggregate or
writeback as part of a read-only health check.
