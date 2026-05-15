# Phase 187 - Stream Outline Lookup During Memory Rebuild

## Problem

`rebuild_longform_memory` used `_outline_lookup` to load the latest outline, but
that helper selected the full `Outline.chapters` JSON column through the ORM.
After the smoke project started seeding thousand-chapter outlines, memory rebuild
again had a wide JSON read on a core million-word path.

## Change

- Added a regression test that rebuilds memory with a 1000-chapter outline and
  captures SQL.
- Replaced the ORM outline load with `json_each(outlines.chapters)` iteration.
- Kept the in-memory chapter-index lookup shape unchanged for memory creation.

## Tests

- RED: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_rebuild_longform_memory_does_not_select_full_outline_json -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_rebuild_longform_memory_does_not_select_full_outline_json -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py -q` (`39 passed`)
- GREEN: `backend\.venv\Scripts\python.exe scripts\longform_scale_smoke.py --chapters 1000 --words-per-chapter 1000 --cleanup`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` (`593 passed`)
- GREEN: `npm run test:unit` from `frontend` (`402 passed`)
- GREEN: `npm run build` from `frontend`
- GREEN: `git diff --check`
- GREEN: DeepSeek key scan returned `NO_MATCH`

## Result

Memory rebuild no longer selects the full outline chapter JSON column. The
1000-chapter smoke remained stable with `memory_rebuild=283ms`, bounded narrative
plan windows, and `elapsed_ms=8807`.
