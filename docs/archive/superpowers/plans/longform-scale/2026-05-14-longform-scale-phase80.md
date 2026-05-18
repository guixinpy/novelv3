# Longform Scale Phase 80 - Consistency Issue Pagination

## Goal

Keep consistency issue review scalable as long novels accumulate many checks across hundreds or thousands of chapters.

## Problem

`GET /api/v1/projects/{project_id}/consistency/issues` returned all saved issues for a project. In longform writing, repeated chapter checks can create a large issue history that should be paged instead of loaded as one payload.

## Success Criteria

- The consistency issues endpoint accepts `offset` and `limit`.
- The response includes `issues`, `total`, `offset`, `limit`, and `has_more`.
- Results have deterministic chapter-order paging.
- The frontend API can request pages while the Athena store remains compatible with the previous array shape.
- Backend and frontend verification remain green.

## Verification

- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_consistency.py -k "bounded_page" -q --basetemp .tmp\pytest`  
  Result: `1 passed, 5 deselected`
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_consistency.py -q --basetemp .tmp\pytest`  
  Result: `6 passed`
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests -q --basetemp .tmp\pytest`  
  Result: `508 passed`
- `D:\DevTools\Nodejs\Nodejs22.18\npm.cmd run build`  
  Result: TypeScript passed; Vite build passed after rerunning with write permission for `backend/static/assets`
- `D:\DevTools\Nodejs\Nodejs22.18\npm.cmd run test:unit`  
  Result: `60 passed`, `364 passed`

