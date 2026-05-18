# Longform Scale Phase 79 - Revision History Pagination

## Goal

Prevent chapter revision history from becoming an unbounded project-level payload in long-running novels.

## Problem

`GET /api/v1/projects/{project_id}/revisions` returned every revision in one response. For thousand-chapter projects with repeated edits, this can grow into a large and slow API payload even when the UI only needs the first page.

## Success Criteria

- The revisions endpoint accepts `offset` and `limit`.
- The response includes `revisions`, `total`, `offset`, `limit`, and `has_more`.
- The page size is bounded to protect the server.
- The frontend API client exposes the paginated response type.
- Existing revision submit, draft, regenerate, and longform maintenance paths remain green.

## Verification

- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapter_revisions.py -k "bounded_page" -q --basetemp .tmp\pytest`  
  Result: `1 passed, 14 deselected`
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapter_revisions.py -q --basetemp .tmp\pytest`  
  Result: `15 passed`
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests -q --basetemp .tmp\pytest`  
  Result: `507 passed`
- `D:\DevTools\Nodejs\Nodejs22.18\npm.cmd run build`  
  Result: passed after rerunning with write permission for `backend/static/assets`

