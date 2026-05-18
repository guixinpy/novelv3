# Phase 260 - Continue Writing After Existing Chapters

## Goal

Starting writing on an existing long-form project should continue after the
latest generated chapter instead of resetting to chapter 1. This avoids
accidental rewrites when a project already contains hundreds or thousands of
chapters but has no persisted writing state yet.

## TDD Evidence

- RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing.py -q -k "continues_after_latest"`
  - Failed because `/writing/start` returned `current_chapter=1` after three
    generated chapters existed.
- GREEN:
  - Same focused command passed with `1 passed`.
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing.py -q`
    passed with `7 passed`.

## Changes

- `WritingStateService.start()` now initializes missing writing state at
  `max(generated chapter index) + 1`.
- The lookup uses an aggregate chapter index query and does not load chapter
  bodies.
- Existing persisted writing state still keeps its current chapter.

## Verification Evidence

- `backend\.venv\Scripts\python.exe -m pytest backend/tests -q` passed with
  `653 passed in 57.57s`.
- `npm run build` passed.
- `npm run test:unit -- --run` passed with `62 passed` files and `420 passed`
  tests.
- `git diff --check` passed.
- DeepSeek key scan returned `NO_MATCH`.
