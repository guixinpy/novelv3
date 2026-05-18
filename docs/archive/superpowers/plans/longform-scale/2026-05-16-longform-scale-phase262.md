# Longform Scale Phase 262 - Workspace Bootstrap Writing State

## Goal

Make Hermes cold start include the current writing state in `workspace-bootstrap`, so a longform project can restore project metadata, lightweight workspace data, dialogs, and write progress with one request.

## Scope

- Add `writing_state` to backend workspace bootstrap response.
- Add `writing_state` to frontend bootstrap types.
- Store and reset writing state in the project Pinia store.

## RED

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_workspace_bootstrap.py -q -k "returns_project_session_bundle"`
  - Failed with `KeyError: 'writing_state'`.
- `npm run test:unit -- --run src/stores/project.workspace.test.ts -t "workspace bootstrap 会填充|resetProjectScopedState"`
  - Failed because `store.writingState` was not populated from bootstrap and was not reset.

## GREEN

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_workspace_bootstrap.py -q -k "returns_project_session_bundle"`
  - `1 passed, 7 deselected`
- `npm run test:unit -- --run src/stores/project.workspace.test.ts -t "workspace bootstrap 会填充|resetProjectScopedState"`
  - `2 passed, 18 skipped`

## Related Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_workspace_bootstrap.py -q`
  - `8 passed`
- `npm run test:unit -- --run src/stores/project.workspace.test.ts`
  - `20 passed`

## Full Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
  - `654 passed`
- `npm run build`
  - `vue-tsc --noEmit && vite build` passed
- `npm run test:unit -- --run`
  - `62 passed`, `421 passed`
- `git diff --check`
  - Passed
- DeepSeek key scan
  - `NO_MATCH`
