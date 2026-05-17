# Longform Scale Phase 308 - Allow Project Model Switching From Project List

## Goal

Make long-running projects easier to operate when the user needs to switch generation strategy after creation.

## Finding

The backend already accepts `ai_model` updates and generation honors the stored project model, but the frontend only exposed model selection during project creation. A long-form project could not switch between `deepseek-chat` and `deepseek-reasoner` from the project list.

## TDD Evidence

RED:

```powershell
npm run test:unit -- --run src/views/ProjectListView.test.ts
```

Observed failure:

```text
Unable to get [data-testid="project-row-ai-model-project-1"]
```

GREEN:

```powershell
npm run test:unit -- --run src/views/ProjectListView.test.ts
```

Observed result:

```text
6 passed
```

## Change

- Added `api.updateProject(id, data)` for `PATCH /projects/{id}`.
- Added `store.updateProjectModel(id, aiModel)` and local project cache refresh.
- Added a compact model select column in the project list, with row-click propagation stopped.

## Verification

Full phase gate:

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` -> `703 passed`
- `npm run build` -> passed
- `npm run test:unit -- --run` -> `442 passed`
- Browser check for project-list model selector -> PATCH body `{"ai_model":"deepseek-reasoner"}` and select value updated
- `git diff --check` -> passed
- DeepSeek key scan -> `NO_MATCH`
