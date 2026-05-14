# Phase 145 - Workspace bootstrap setup summary

## Goal

Keep workspace cold-start lightweight by avoiding large `Setup` JSON columns in `/workspace-bootstrap`.

## Why

Million-word projects can accumulate large world-building, character, and concept payloads. The bootstrap endpoint only needs enough metadata to render the shell and decide whether the setup exists; loading full setup JSON on every project entry wastes database IO and response size.

## TDD

RED:

- Added a backend SQL-capture test proving bootstrap must not select `setups.world_building`, `setups.characters`, or `setups.core_concept`.
- Added a frontend store test proving a partial setup from bootstrap must not be treated as a complete setup cache entry.

GREEN:

- `build_project_diagnosis(...)` now checks only `Setup.status`.
- Workspace bootstrap now returns a setup summary with id, project id, status, and timestamps.
- Added `setup_partial` to the bootstrap schema and frontend API type.
- Frontend cache freshness now skips partial setup payloads, so the setup view still loads full setup data on demand.

## Verification

- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_workspace_bootstrap.py backend\tests\test_projects.py -q` -> 18 passed
- `npm run test:unit -- src/stores/project.workspace.test.ts src/stores/chat.workspace.test.ts` -> 40 passed
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests -q` -> 568 passed
- `npm run test:unit` -> 60 files / 376 tests passed
- `npm run build` -> passed
- `git diff --check` -> passed
- Exact DeepSeek key scan -> no matches
- `.\backend\.venv\Scripts\python.exe scripts\longform_scale_smoke.py --chapters 1000 --words-per-chapter 1000 --cleanup` -> passed, 1,000 chapters / 1,000,000 words, elapsed 21,723 ms
