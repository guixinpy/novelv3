# Phase59 Report: Longform Batch Inspect

## Summary

Phase59 added `inspect_longform_chapter_batch`, a read-only Writing Agent tool for inspecting materialized `longform_chapter_batch` background tasks.

This closes the immediate observability gap created by Phase58: the Agent can now inspect queued longform batches, their chapter range, plan hash, queue policy, DAG summary, progress/resume state, and execution readiness before any batch worker is implemented.

## Reference Assimilation

Subagent reference review highlighted:

- `openclaw`: useful DTO split between task ledger, flow state, status counts, and compact focus projection.
- `hermes-agent`: checkpoint/run-attempt/event-cursor ideas are important, but should not be executed through a generic Kanban runtime.
- `openhuman`: lightweight batch status tables, lanes, and micro-compact statistics are useful for future queue views.

Adopted in Phase59:

- compact queue projection: `summary.by_status`, `queue.depth`, `queue.active`, `queue.terminal`;
- selected task focus detail;
- explicit `execution_readiness` showing `materialized_only`;
- resume payload separated from progress payload.

Not adopted:

- worker claim/heartbeat systems;
- full event cursor store;
- batch run attempts table;
- GitHub/PR-style status projection;
- runtime LLM compression inside inspect.

## Changes

- Added `backend/app/services/writing_agent/batch_queue_inspector.py`.
- Registered `inspect_longform_chapter_batch` as an internal non-blocking read tool.
- Added a static read-only executor adapter.
- Added registry, executor, and API tests for queue inspection.
- Added selected-task missing behavior with `status: "not_found"`.
- Added compact projection fields for status counts and active/terminal queue overview.

## Tool Contract

List/detail output:

- `status: "completed"`;
- `summary.total`;
- `summary.returned`;
- `summary.by_status`;
- `queue.depth`;
- `queue.active`;
- `queue.terminal`;
- compact `tasks`;
- optional `selected_task`.

Selected task includes:

- task id/type/status;
- plan hash;
- chapter range;
- queue policy;
- batch payload;
- DAG summary;
- tool requests;
- progress;
- resume hints;
- execution readiness.

Missing selected task returns:

- `status: "not_found"`;
- empty task list;
- `selected_task: null`;
- trace rejection reason `selected_task_not_found`.

## Verification

RED registry/executor:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py -q -k "longform_chapter_batch"
```

Result before implementation: `3 failed, 6 passed, 19 deselected`.

RED API:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "inspect_longform_chapter_batch"
```

Result before implementation: failed because `inspect_longform_chapter_batch` was unsupported.

RED compact projection:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "inspects_longform_chapter_batch_queue"
```

Result before compact projection implementation: failed because `summary.by_status` was missing.

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py -q -k "longform_chapter_batch"
```

Result: `17 passed, 148 deselected in 0.87s`.

T1 Agent and queue verification:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_writing_agent_planner.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_tool_registry.py tests\test_background.py -q
```

Result: `204 passed in 12.84s`.

## Novel Progress

No new novel chapter was generated. This phase continues task queue infrastructure work so future real generation can run through observable, inspectable, recoverable batch records instead of synchronous ad hoc requests.

## Discovered Issues

- Phase58 materialized queue tasks were durable but not inspectable by the Agent.
- The first inspector version lacked compact status counts; this was added after a failing test.

## Fixed Issues

- Added project-scoped read-only inspection for `longform_chapter_batch` tasks.
- Added `not_found` behavior for missing selectors.
- Added queue compact projection.

## Remaining Boundary

The tool does not execute a batch. It also does not yet expose:

- per-node event cursor;
- batch run attempts;
- checkpoint manifests;
- resume token lineage;
- frontend queue visualization.

## Next Phase Recommendation

Phase60 should add the first controlled executor skeleton for `longform_chapter_batch` that can mark a batch task running, execute only the first safe read/preflight nodes, checkpoint progress, and stop before generating prose. That keeps execution incremental and recoverable.
