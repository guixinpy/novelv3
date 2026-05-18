# Longform Scale Phase 316 - Surface Writing Task Diagnostics

## Goal

Make continuous writing task diagnostics visible in Hermes while keeping background task polling compact.

## Finding

Phase 315 aggregates chapter word-target drift and post-generation warnings into `result.generation_diagnostics`, but compact polling stripped the field and the Hermes dashboard had no place to show it. For long runs, that hides batch-level risk until a user opens raw traces.

## TDD Evidence

Backend RED:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background.py::test_get_background_task_compact_includes_generation_diagnostics -q
```

Observed failure:

```text
AssertionError: assert None == {'generation_diagnostics': ...}
```

Frontend RED:

```powershell
npm run test:unit -- --run src/stores/project.workspace.test.ts -t "轮询到范围任务进度"
npm run test:unit -- --run src/components/shared/ProjectDashboard.test.ts -t "generation diagnostics"
```

Observed failures:

```text
expected undefined to deeply equal { word_target: ... }
expected ... to contain '本轮诊断'
```

GREEN:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background.py::test_get_background_task_compact_includes_generation_diagnostics backend\tests\test_background.py::test_get_background_task_compact_includes_range_progress backend\tests\test_background.py::test_get_background_task_compact_does_not_select_heavy_task_fields -q
npm run test:unit -- --run src/stores/project.workspace.test.ts -t "轮询到范围任务进度"
npm run test:unit -- --run src/components/shared/ProjectDashboard.test.ts -t "generation diagnostics"
```

Observed result:

```text
3 passed
1 passed
1 passed
```

## Change

- Compact background task responses now include safe `generation_diagnostics` alongside progress for `generate_chapter` tasks, including terminal states.
- The project store preserves the latest writing task diagnostics during polling and clears them when a new writing run starts or the project scope resets.
- Hermes passes writing diagnostics into the dashboard.
- The dashboard shows a compact Chinese summary for word-target drift and post-generation maintenance warnings.

## Verification

Stage gate:

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background.py backend\tests\test_writing.py -q` -> `62 passed`
- `npm run test:unit -- --run src/stores/project.workspace.test.ts src/components/shared/ProjectDashboard.test.ts` -> `41 passed`

Full gate:

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` -> `706 passed`
- `npm run build` in `frontend` -> passed
- `npm run test:unit -- --run` in `frontend` -> `446 passed`
- `git diff --check` -> passed
- DeepSeek key scan -> `NO_MATCH`

Browser smoke:

- Browser plugin tool was unavailable; Playwright default browser was not installed, so fallback used local Chrome channel.
- `http://127.0.0.1:5173/projects/b9d50481-6f5c-4f54-9b60-984c43e40808/hermes` rendered dashboard sections with no material failed responses and no page errors.
