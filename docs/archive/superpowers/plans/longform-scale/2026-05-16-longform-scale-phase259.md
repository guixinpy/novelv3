# Phase 259 - Persist Background Action Failures

## Goal

Persist a terminal failed dialog message when a background action raises an
exception. This makes long-running generation failures durable across reloads
instead of relying only on the client-side compact task fallback.

## TDD Evidence

- RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_dialogs.py -q -k "background_action_work_records_failure_message"`
  - Failed because there was no testable background action work helper and no
    exception-to-dialog failure path.
- GREEN:
  - Same focused command passed with `1 passed`.
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_dialogs.py backend/tests/test_dialog_messages_pagination.py -q`
    passed with `57 passed`.

## Changes

- Added `build_action_background_work()` for background action execution.
- Background action exceptions now call `ActionResultService.record_completion()`
  with a failed result before re-raising to let `LocalTaskRunner` mark the task
  failed.
- `_execute_action_background()` now uses the shared work builder.

## Verification Evidence

- `backend\.venv\Scripts\python.exe -m pytest backend/tests -q` passed with
  `652 passed in 55.07s`.
- `npm run build` passed.
- `npm run test:unit -- --run` passed with `62 passed` files and `420 passed`
  tests.
- `git diff --check` passed.
- DeepSeek key scan returned `NO_MATCH`.
