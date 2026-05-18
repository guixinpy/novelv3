# Longform Scale Phase 270 - Writing Controls Queue Chapter Generation

## Goal

Make Hermes writing controls start real chapter generation instead of only setting `writing_states.status = running`. A longform writing session must create a tracked background task for the current chapter.

## Scope

- `/writing/start` creates a `generate_chapter` background task for the resolved current chapter.
- `/writing/resume` creates a `generate_chapter` background task for the paused current chapter.
- Reuse the existing background task runner and chapter generation endpoint behavior.

## RED

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py -q -k "start_creates_generate_chapter_task or resume_creates_generate_chapter_task"`
  - Failed because start/resume returned `running` state but created no `generate_chapter` background task.

## GREEN

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py -q -k "start_creates_generate_chapter_task or resume_creates_generate_chapter_task"`
  - `2 passed`, `8 deselected`
- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py -q`
  - `10 passed`

## Full Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
  - `660 passed`
- `npm run build`
  - `vue-tsc --noEmit && vite build` passed
- `npm run test:unit -- --run`
  - `64 passed`, `430 passed`
- `git diff --check`
  - Passed
- DeepSeek key scan
  - `NO_MATCH`
