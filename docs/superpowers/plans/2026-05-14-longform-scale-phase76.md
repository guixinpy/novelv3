# Longform Scale Phase 76

## Goal

Make local background tasks recover visibly after a process restart.

## Problem

Longform writing and review workflows can run background jobs. If the local process exits while a task is `running`, that task can otherwise remain permanently running after restart, which makes recovery ambiguous for thousand-chapter projects.

## Success Criteria

1. Application startup invokes the existing interrupted-task cleanup service.
2. Any previously `running` task can be marked `failed` with the existing interruption error.
3. The startup cleanup closes its database session.
4. Cleanup failure is logged but does not prevent the app from starting.
5. Backend tests remain green.

## Steps

1. Add a failing startup test that expects interrupted running tasks to be marked through `BackgroundTaskService`.
2. Add a FastAPI lifespan startup hook that calls `fail_interrupted_background_tasks`.
3. Keep the startup path warning-free by using lifespan instead of deprecated `on_event`.
4. Run the focused startup test, full background tests, backend full tests, diff check, and secret scan.

## Verification

1. `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background.py -k "app_startup_marks" -q --basetemp .tmp\pytest` -> 1 passed.
2. `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background.py -q --basetemp .tmp\pytest` -> 17 passed.
3. `backend\.venv\Scripts\python.exe -m pytest backend\tests -q --basetemp .tmp\pytest` -> 504 passed.
4. `git diff --check` -> clean.
5. DeepSeek key exact scan -> no matches.
