# Longform Scale Phase 88: Lightweight Workspace Outline Bootstrap

## Goal

Keep project cold start stable when an outline contains hundreds or thousands of chapter planning records. Workspace bootstrap should not read or return the full outline JSON body on first load.

## Change

- Added a regression test proving workspace bootstrap does not select `outlines.chapters`, `outlines.plotlines`, or `outlines.foreshadowing`.
- Changed bootstrap outline payload to a summary object with status and `total_chapters`, leaving heavy arrays empty.
- Added `outline_partial` to the bootstrap response.
- Updated the frontend project store so partial outlines are not marked as fresh full-outline cache.
- Full outline loading remains available through the dedicated outline endpoint.

## Verification

- Red: `python -m pytest backend/tests/test_workspace_bootstrap.py -k "outline_summary" -q --basetemp .tmp/pytest`
- Red: `npm run test:unit -- src/stores/project.workspace.test.ts -t "partial outline"`
- Green: same focused backend/frontend commands.
- Bootstrap suite: `python -m pytest backend/tests/test_workspace_bootstrap.py -q --basetemp .tmp/pytest`
- Project store suite: `npm run test:unit -- src/stores/project.workspace.test.ts`
