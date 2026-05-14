# Longform Scale Phase 77

## Goal

Make background task history pageable for long-running longform projects.

## Problem

The project background task endpoint returned a fixed 20-task window without total metadata. A thousand-chapter project can accumulate many generation, review, repair, and indexing tasks, so fixed history prevents reliable UI paging and operational diagnosis.

## Success Criteria

1. `GET /api/v1/projects/{project_id}/background-tasks` accepts `offset` and `limit`.
2. The response includes `total`, `offset`, `limit`, and `has_more`.
3. Existing `tasks` response field remains compatible.
4. The endpoint keeps a bounded maximum page size.
5. Backend tests remain green.

## Steps

1. Add a failing API test for a project with 30 background tasks.
2. Add FastAPI query params and count/offset/limit query logic.
3. Preserve the existing task summary shape.
4. Run focused background tests, backend full tests, diff check, and secret scan.

## Verification

1. `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background.py -k "paginates_large_project_history" -q --basetemp .tmp\pytest` -> 1 passed.
2. `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background.py -q --basetemp .tmp\pytest` -> 18 passed.
3. `backend\.venv\Scripts\python.exe -m pytest backend\tests -q --basetemp .tmp\pytest` -> 505 passed.
4. `git diff --check` -> clean.
5. DeepSeek key exact scan -> no matches.
