# Longform Scale Phase 83 - Athena Timeline Latest Window

## Goal

Prevent Athena narrative timeline and graph entry from loading every world timeline event in thousand-chapter projects.

## Problem

`GET /api/v1/projects/{project_id}/athena/state/timeline` returned all anchors and events for the current profile. Large projects can accumulate hundreds or thousands of timeline entries, while the default authoring view usually needs the current/latest window first.

## Success Criteria

- The timeline endpoint supports `latest`, `offset`, and `limit`.
- Latest-window responses return the newest page sorted back into chronological order.
- The response includes anchor and event totals, offsets, limits, and `has_more` flags.
- The Athena store requests a bounded latest timeline window by default.
- Existing narrative timeline and graph tests remain green.

## Verification

- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_world_frontend_api.py -k "latest_bounded_window" -q --basetemp .tmp\pytest`  
  Result: failed before implementation because `events_total` was missing; passed after implementation with `1 passed, 24 deselected`
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_world_frontend_api.py -q --basetemp .tmp\pytest`  
  Result: `25 passed`
- `D:\DevTools\Nodejs\Nodejs22.18\npm.cmd run test:unit -- src/views/athenaSectionLoader.test.ts src/views/AthenaView.test.ts src/components/athena/NarrativeAtlasView.test.ts`  
  Result: `3 passed`, `25 passed`
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests -q --basetemp .tmp\pytest`  
  Result: `511 passed`
- `D:\DevTools\Nodejs\Nodejs22.18\npm.cmd run test:unit`  
  Result: `60 passed`, `366 passed`
- `D:\DevTools\Nodejs\Nodejs22.18\npm.cmd run build`  
  Result: passed

