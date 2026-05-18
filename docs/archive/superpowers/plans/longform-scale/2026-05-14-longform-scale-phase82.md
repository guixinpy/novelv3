# Longform Scale Phase 82 - World Fact Claim Pagination Metadata

## Goal

Make world-model fact browsing reliable for large truth ledgers by returning explicit pagination metadata instead of relying on page-size heuristics.

## Problem

`GET /api/v1/projects/{project_id}/world-model/facts` accepted `offset` and `limit`, but returned only a list. The frontend inferred `has_more` from `claims.length === page_size`, which misclassifies an exact final page as having more data.

## Success Criteria

- The world fact claims endpoint returns `claims`, `total`, `offset`, `limit`, and `has_more`.
- Empty projects return the same paginated shape.
- The world-model store remains compatible with the previous array response.
- The store uses backend `has_more` when available.

## Verification

- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_world_frontend_api.py -k "fact_claims_returns_bounded_page" -q --basetemp .tmp\pytest`  
  Result: `1 passed, 23 deselected`
- `D:\DevTools\Nodejs\Nodejs22.18\npm.cmd run test:unit -- src/stores/worldModel.test.ts`  
  Result: `29 passed`
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_world_frontend_api.py -q --basetemp .tmp\pytest`  
  Result: `24 passed`
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests -q --basetemp .tmp\pytest`  
  Result: `510 passed`
- `D:\DevTools\Nodejs\Nodejs22.18\npm.cmd run test:unit`  
  Result: `60 passed`, `366 passed`
- `D:\DevTools\Nodejs\Nodejs22.18\npm.cmd run build`  
  Result: TypeScript passed; Vite build passed after rerunning with write permission for `backend/static/assets`

