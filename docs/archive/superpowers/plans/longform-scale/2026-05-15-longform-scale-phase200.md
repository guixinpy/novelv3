# Phase 200 - Bound Setup Fallback Context

## Problem

When a project has no formal world-model profile, Athena falls back to the
Setup draft for dialog and chapter context. That path previously serialized the
entire `world_building` and `core_concept` JSON payloads into the prompt. A
large early-stage longform project could therefore send oversized setup drafts
into every Athena or chapter-generation context call.

## Change

- Added a regression test with 100 draft characters and oversized Setup JSON.
- Capped Setup fallback character names at 20 and reports the omitted count.
- Compacted Setup world-building text to 1200 characters.
- Compacted Setup core-concept text to 800 characters.
- Reused the same bounded fallback in:
  - Athena dialog context when no profile exists.
  - Chapter context package when no profile exists.

## Tests

- RED: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_athena_dialog.py::test_setup_fallback_context_bounds_large_setup_drafts -q`
  - failed because the old context still emitted complete long Setup payloads and omitted no truncation signal.
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_athena_dialog.py::test_setup_fallback_context_bounds_large_setup_drafts -q` (`1 passed`)
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_athena_dialog.py backend\tests\test_prompting_dialog_migration.py -q` (`27 passed`)
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` (`602 passed`)
- GREEN: `npm run build` from `frontend`
- GREEN: `npm run test:unit` from `frontend` (`407 passed`)
- GREEN: `git diff --check`
- GREEN: DeepSeek key scan returned `NO_MATCH`

## Result

Setup fallback is now bounded before a project has been converted into the
canonical world model. This keeps early longform planning usable without letting
large setup drafts dominate every prompt context.
