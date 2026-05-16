# Phase 261 - Readable Writing State

## Goal

Expose current writing state through a lightweight API so the frontend can
refresh after reloads, task failures, and long-running writing sessions. This is
a foundation for stable thousand-chapter writing control.

## TDD Evidence

- RED backend:
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing.py -q -k "writing_state_endpoint"`
  - Failed because `GET /writing/state` fell through to the static frontend
    fallback instead of returning JSON state.
- RED frontend:
  - `npm run test:unit -- --run src/api/client.worldModel.test.ts -t "getWritingState"`
  - Failed because `api.getWritingState` did not exist.
- GREEN:
  - Backend focused command passed with `1 passed`.
  - Frontend focused command passed with `1 passed`.
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing.py -q`
    passed with `8 passed`.
  - `npm run test:unit -- --run src/api/client.worldModel.test.ts` passed with
    `7 passed`.

## Changes

- Added `GET /api/v1/projects/{project_id}/writing/state`.
- Added frontend `WritingState` type and `api.getWritingState(projectId)`.
- Existing start/pause/resume/retry behavior is unchanged.

## Verification Evidence

- `backend\.venv\Scripts\python.exe -m pytest backend/tests -q` passed with
  `654 passed in 55.54s`.
- `npm run build` passed.
- `npm run test:unit -- --run` passed with `62 passed` files and `421 passed`
  tests.
- `git diff --check` passed.
- DeepSeek key scan returned `NO_MATCH`.
