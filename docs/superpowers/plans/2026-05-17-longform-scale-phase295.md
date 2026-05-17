# Longform Scale Phase 295 - Interrupted Writing State Recovery

## Assumption

The app may restart while a long continuous writing task is pending or running.

## Risk

Startup already marks interrupted background tasks as failed. However, the associated `writing_state` could remain `running`, leaving Hermes showing "写作中" with no active worker after restart.

## Change

1. `BackgroundTaskService.fail_interrupted_running_tasks()` now also marks `writing_states` as failed for active `generate_chapter` and `retry_chapter` tasks.
2. The write is bulk-based with a subquery over active writing task project IDs; it does not load heavy task payload/result rows.
3. Non-writing background tasks still only update task status.

## Verification

- Red: `backend\\.venv\\Scripts\\python.exe -m pytest backend\\tests\\test_background.py::test_background_task_service_marks_interrupted_writing_state_failed -q` failed because writing state stayed `running`.
- Green: `backend\\.venv\\Scripts\\python.exe -m pytest backend\\tests\\test_background.py -q` passed with 33 tests.
- Full verification will run before commit.
