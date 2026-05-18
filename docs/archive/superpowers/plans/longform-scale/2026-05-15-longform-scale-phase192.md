# Phase 192 - Window Athena Generation Responses

## Problem

Read paths for narrative plans are now windowed, but the Athena
`/evolution/plan/generate` endpoint still returned the full generated outline or
storyline payload. For a thousand-chapter project, clicking generate could push
the full plan back into the frontend store immediately after persistence.

## Change

- Added regression tests for Athena storyline and outline generation responses.
- Kept generation persistence unchanged: the database still stores the full
  generated plan.
- Changed the Athena generate endpoint to default to `response_mode=window` and
  return the target's bounded plan window.
- Preserved `response_mode=full` for explicit compatibility/debug callers.

## Tests

- RED: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_athena_evolution_generation_windows.py -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_athena_evolution_generation_windows.py -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_athena_evolution_generation_windows.py backend\tests\test_prompting_generation_migration.py backend\tests\test_outlines.py backend\tests\test_storylines.py backend\tests\test_athena_evolution_plan.py -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` (`597 passed`)
- GREEN: `npm run build` from `frontend`
- GREEN: `npm run test:unit` from `frontend` (`405 passed`)
- GREEN: `git diff --check`
- GREEN: DeepSeek key scan returned `NO_MATCH`

## Result

Athena generation now writes complete narrative plans but returns bounded response
windows by default. This keeps post-generation UI state aligned with the same
longform safety model as regular narrative reads.
