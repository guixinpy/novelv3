# Longform Scale Phase 265 - Chapter Generation Syncs Writing State

## Goal

Keep persisted writing progress aligned with actual chapter generation. Manual generation and retry paths should leave the reloadable writing state in a truthful state.

## Scope

- Mark the requested chapter as running before the model call.
- Mark writing state failed when model generation fails or returns empty normalized content.
- Mark writing state idle for the generated chapter after the chapter write succeeds.

## RED

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py -q -k "writing_state"`
  - Failed because successful chapter generation left `current_chapter=1`.
  - Failed because model errors left writing state `idle`.

## GREEN

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py -q -k "writing_state"`
  - `2 passed`, `27 deselected`

## Related Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py -q`
  - `29 passed`
- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py -q`
  - `8 passed`

## Full Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
  - `656 passed`
- `npm run build`
  - `vue-tsc --noEmit && vite build` passed
- `npm run test:unit -- --run`
  - `62 passed`, `424 passed`
- `git diff --check`
  - Passed
- DeepSeek key scan
  - `NO_MATCH`
