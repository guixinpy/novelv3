# Longform Scale Phase 90: Lightweight Workspace Storyline Bootstrap

## Goal

Keep project cold start stable when storylines contain many plotlines and foreshadowing records. Workspace bootstrap should expose counts for the dashboard without loading the full storyline JSON body.

## Change

- Added SQL-level backend tests proving bootstrap does not select full `storylines.plotlines` / `storylines.foreshadowing` JSON values.
- Changed bootstrap storyline payload to a summary with empty arrays plus `plotlines_count` and `foreshadowing_count`.
- Added `storyline_partial` to the bootstrap response.
- Updated the frontend store so partial storylines are not marked as complete cache.
- Updated the dashboard to use count metadata when arrays are intentionally partial.

## Verification

- Red: `python -m pytest backend/tests/test_workspace_bootstrap.py -k "storyline_summary or project_session_bundle" -q --basetemp .tmp/pytest`
- Red: `npm run test:unit -- src/stores/project.workspace.test.ts -t "partial storyline"`
- Red: `npm run test:unit -- src/components/shared/ProjectDashboard.test.ts -t "storyline count metadata"`
- Green: same focused commands.
- Bootstrap suite: `python -m pytest backend/tests/test_workspace_bootstrap.py -q --basetemp .tmp/pytest`
- Frontend focused suite: `npm run test:unit -- src/stores/project.workspace.test.ts src/components/shared/ProjectDashboard.test.ts`
