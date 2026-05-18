# Phase 191 - Bound Legacy Narrative Reads

## Problem

The Athena evolution-plan path is windowed, and the frontend no longer calls the
old `/outline` and `/storyline` endpoints for normal workspace refreshes. Those
legacy endpoints still returned full JSON payloads by default, so an external or
old internal caller could bypass the longform safeguards and load thousand-
chapter narrative data in one response.

## Change

- Added regression tests for legacy `GET /outline` and `GET /storyline`.
- Reused `get_evolution_plan_window()` for default legacy reads.
- Added bounded chapter, plotline, milestone, and foreshadowing metadata to the
  legacy response schemas.
- Preserved `mode=full` for callers that deliberately need the old full payload.
- Extended the shared narrative-plan window helper with small metadata fields so
  its windowed dictionaries can satisfy both Athena and legacy response shapes.

## Tests

- RED: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_legacy_narrative_windows.py -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_legacy_narrative_windows.py -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_legacy_narrative_windows.py backend\tests\test_outlines.py backend\tests\test_storylines.py backend\tests\test_athena_evolution_plan.py -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` (`595 passed`)
- GREEN: `npm run build` from `frontend`
- GREEN: `npm run test:unit` from `frontend` (`405 passed`)
- GREEN: `git diff --check`
- GREEN: DeepSeek key scan returned `NO_MATCH`

## Result

Legacy narrative read endpoints now default to bounded windows and avoid selecting
the full JSON columns for outline/storyline arrays. This removes a remaining
escape hatch around the longform plan-window path while keeping explicit full
reads available for compatibility.
