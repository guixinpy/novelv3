# Longform Scale Phase 81 - Version History Pagination

## Goal

Keep version history usable and bounded as million-word projects accumulate many saves, regenerations, rollbacks, and revision outputs.

## Problem

`GET /api/v1/projects/{project_id}/versions` returned every version summary in one response. The Hermes version modal also had no way to load additional pages once the backend becomes bounded.

## Success Criteria

- The versions endpoint accepts `offset` and `limit`.
- The response includes `versions`, `total`, `offset`, `limit`, and `has_more`.
- Version summaries still avoid selecting large `content` bodies.
- Workspace bootstrap includes version paging metadata.
- The project store can load the first version page and append more.
- The version modal exposes loaded/total count and a load-more action.

## Verification

- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_versions.py -k "bounded_page" -q --basetemp .tmp\pytest`  
  Result: `1 passed, 6 deselected`
- `D:\DevTools\Nodejs\Nodejs22.18\npm.cmd run test:unit -- src/stores/project.workspace.test.ts`  
  Result: `15 passed`
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_versions.py -q --basetemp .tmp\pytest`  
  Result: `7 passed`
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_workspace_bootstrap.py -q --basetemp .tmp\pytest`  
  Result: `4 passed`
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests -q --basetemp .tmp\pytest`  
  Result: `509 passed`
- `D:\DevTools\Nodejs\Nodejs22.18\npm.cmd run test:unit`  
  Result: `60 passed`, `365 passed`
- `D:\DevTools\Nodejs\Nodejs22.18\npm.cmd run build`  
  Result: TypeScript passed; Vite build passed after rerunning with write permission for `backend/static/assets`

