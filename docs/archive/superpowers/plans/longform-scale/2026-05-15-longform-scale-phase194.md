# Phase 194 - Filter Deep-Check Foreshadowing Candidates

## Problem

The deep consistency checker loaded the full `Storyline.foreshadowing` JSON array
before checking whether any foreshadowing item was overdue. In a long project,
deep-checking one chapter could repeatedly deserialize hundreds or thousands of
foreshadowing records even though only overdue candidates matter.

## Change

- Added a regression test around overdue foreshadowing candidate loading.
- Added `_load_overdue_foreshadowing_candidates()` using SQLite `json_each` and
  `json_extract` to filter candidates by status and resolved chapter.
- Updated `BackgroundAnalyzer.run_deep_check()` to pass only filtered candidates
  into `ForeshadowingChecker`.
- Preserved the existing checker behavior: missing status defaults to `planted`,
  resolved items are ignored, and future items are ignored.

## Tests

- RED: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background_analyzer.py -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background_analyzer.py -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background_analyzer.py backend\tests\test_checkers.py backend\tests\test_consistency.py -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` (`598 passed`)
- GREEN: `npm run build` from `frontend`
- GREEN: `npm run test:unit` from `frontend` (`407 passed`)
- GREEN: `git diff --check`
- GREEN: DeepSeek key scan returned `NO_MATCH`

## Result

Deep consistency checks no longer need to read the full storyline foreshadowing
JSON just to find overdue items. This reduces repeated per-chapter deep-check
work on long novels with large foreshadowing plans.
