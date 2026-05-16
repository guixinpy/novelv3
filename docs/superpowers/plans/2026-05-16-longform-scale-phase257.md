# Phase 257 - Background Task Failure Visibility

## Goal

Make long-running background task failures visible in compact polling paths
without loading heavyweight payload/result fields. Thousand-chapter generation
and maintenance tasks must fail loudly enough for the user to recover.

## TDD Evidence

- RED backend:
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_background.py -q -k "compact_returns_bounded_failure_error"`
  - Failed because compact task detail returned `error=null` for failed tasks.
- RED frontend:
  - `npm run test:unit -- --run src/stores/chat.workspace.test.ts -t "失败但历史缺少终态"`
  - Failed because task polling did not add a fallback failure message when
    history lacked a terminal action result.
- GREEN:
  - Backend focused command passed with `1 passed`.
  - Frontend focused command passed with `1 passed`.

## Changes

- Compact background task detail now returns a 240-character bounded error
  preview only for failed/cancelled tasks.
- Compact task polling still avoids selecting `payload` and `result`.
- Hermes chat task polling now adds a system fallback message when a task reaches
  `failed` or `cancelled` but no terminal history message is available.

## Verification Evidence

- `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_background.py -q`
  passed with `29 passed`.
- `npm run test:unit -- --run src/stores/chat.workspace.test.ts` passed with
  `23 passed`.
- `backend\.venv\Scripts\python.exe -m pytest backend/tests -q` passed with
  `651 passed in 54.92s`.
- `npm run build` passed.
- `npm run test:unit -- --run` passed with `62 passed` files and `419 passed`
  tests.
- `git diff --check` passed.
- DeepSeek key scan returned `NO_MATCH`.
