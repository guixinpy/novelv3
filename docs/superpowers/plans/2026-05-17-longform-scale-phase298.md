# Longform Scale Phase 298 - Recover Writing Task Polling On Bootstrap

## Goal

Keep long-running continuous writing observable after page reload or workspace re-entry.

## Finding

The frontend could keep polling a task started in the current session, but workspace bootstrap only returned `writing_state=running` without the active background task id. After a reload, the dashboard could show "写作中" while no polling loop was attached, so later completion or failure would not refresh the UI.

## TDD Evidence

RED:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py::test_writing_state_endpoint_returns_active_task_id -q
npm run test:unit -- --run src/stores/project.workspace.test.ts -t "恢复后台任务轮询"
```

Observed failures:

```text
KeyError: 'task_id'
Number of calls: 0
```

GREEN:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py backend\tests\test_workspace_bootstrap.py -q
npm run test:unit -- --run src/stores/project.workspace.test.ts
```

Observed results:

```text
33 passed
31 passed
```

## Change

- `WritingStateOut` can now include an optional `task_id`.
- Running writing state resolves the active `generate_chapter` / `retry_chapter` task id.
- Workspace bootstrap omits null fields but includes `task_id` when a task is active.
- Project store resumes polling when bootstrap contains a running writing state with `task_id`.

## Verification

Full phase gate passed:

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` - 689 passed
- `npm run build` - passed
- `npm run test:unit -- --run` - 440 passed
- `git diff --check` - passed
- DeepSeek key scan - `NO_MATCH`
