# Phase 173 - Bounded World Projection Overview

## Problem

Million-word projects accumulate large world-model projections: entities, relations,
presence, occurred events, event links, and fact subject groups. The truth projection
view and review refresh paths previously requested the full current projection, which
can produce large payloads and expensive frontend rendering for thousand-chapter
novels.

## Change

- Added window metadata to `WorldProjectionOut` for each projection map.
- Added query windows to `GET /world-model`:
  - entities
  - relations
  - presence
  - occurred events
  - event links
  - fact subject groups
- Kept Athena `/state` aligned with the same default bounded projection window.
- Updated the frontend API client to serialize projection window params.
- Updated the world-model store to use a default bounded truth projection window.

## Tests

- RED: `backend/tests/test_world_frontend_api.py::test_get_world_model_overview_returns_bounded_projection_window`
- RED: `frontend/src/api/client.worldModel.test.ts` window serialization test
- RED: `frontend/src/stores/worldModel.test.ts` bounded projection request test
- GREEN: target backend and frontend tests
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_world_frontend_api.py -q`
- GREEN: `npm run test:unit`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
- GREEN: `npm run build`
- GREEN: `git diff --check`
- GREEN: DeepSeek key scan returned `NO_MATCH`

## Result

The projection UI and review refresh paths no longer pull unbounded truth projection
payloads by default. The backend still materializes the full projection internally,
so future phases should address source-level projection cost if profiling shows it
dominates response time at very large scale.
