# Phase62 Report: Longform Batch Execute One

## Summary

Phase62 added `execute_longform_chapter_batch`, the first true execution entry for the longform batch chain.

The tool consumes the Phase61 `attempt_manifest` and `approval_contract`, verifies explicit confirmation and hash bindings, rejects drift, calls the existing `generate_chapter` action once, and records execution evidence in `BackgroundTask.result`.

This is still not a general batch runner. It supports only one approved chapter per execution.

## Reference Assimilation

Adopted:

- `openclaw` approval-gated execution: high-risk chapter generation is blocked unless the caller provides the exact approval contract fields.
- `hermes-agent` checkpoint discipline: execution writes a durable checkpoint and keeps history bounded.
- `openhuman` parent-loop orchestration boundary: the executor is a callable Agent tool, not a hidden autonomous runtime.

Not adopted:

- generic host-command approval;
- external runner/heartbeat model;
- automatic resume to the next chapter;
- generic memory backend changes;
- subagent runtime copying.

## Changes

- Added `backend/app/services/writing_agent/batch_execution.py`.
- Registered `execute_longform_chapter_batch` as an internal task-queue write tool.
- Made static Writing Agent adapters async-capable.
- Extended `inspect_longform_chapter_batch` selected task details with:
  - `batch_execution_result`;
  - execution readiness status `approval_contract_ready` or `phase62_executed`.
- Added tests for:
  - registry contract;
  - executor metadata and async dispatch;
  - approved one-chapter execution;
  - missing confirmation blocker;
  - hash mismatch blocker;
  - chapter state drift blocker;
  - inspector visibility of execution evidence.

## Tool Contract

Input:

- `task_id`;
- `confirm_execute: true`;
- `attempt_manifest_hash`;
- `approval_contract_hash`.

Success output:

- `status: "completed"`;
- `chapter_index`;
- `executed_chapter_indexes`;
- `generation`;
- `execution_checkpoint`;
- `batch_execution_result`;
- `evidence`;
- `side_effects`.

Blocked output:

- `status: "blocked"`;
- `reason`;
- no chapter generation attempt.

## Side Effect Boundary

Allowed:

- call `ActionExecutionService.execute("generate_chapter")` once;
- create or replace the selected chapter through the existing generation path;
- write `batch_execution_result`;
- append a `chapter_generation` execution checkpoint;
- update range progress through `BackgroundTaskService.mark_range_progress`.

Explicitly skipped:

- `LocalTaskRunner`;
- auto-resume to next chapter;
- quality review;
- continuity review;
- world-model resolution;
- revision steps.

Inherited from `generate_chapter`:

- post-generation maintenance hooks already inside the existing chapter generation path, including Athena/retrieval/longform-memory related updates where that path performs them.

## Verification

RED focused tests:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py -q -k "execute_longform_chapter_batch"
```

Result before implementation: `6 failed, 3 passed, 173 deselected`.

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py -q -k "execute_longform_chapter_batch"
```

Result: `9 passed, 173 deselected in 0.57s`.

Batch chain regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py -q -k "longform_chapter_batch"
```

Result: `34 passed, 148 deselected in 1.85s`.

T1 related regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_writing_agent_planner.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_tool_registry.py tests\test_background.py -q
```

Result: `221 passed in 13.81s`.

Static checks:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

Result:

- `git diff --check` passed; it reported only the existing line-ending normalization warning for `backend/tests/test_writing_agent_runs.py`.
- secret scan returned no matches.

## Novel Progress

No production novel chapter was generated in this phase. The execution path was verified with a monkeypatched `generate_chapter` call in tests to avoid spending model calls before the approval-consuming runner is stable.

## Discovered Issues

- Phase61 produced an auditable approval contract, but no tool consumed it.
- Existing static Writing Agent adapters could not await async handlers, which blocked execution tools from using async services.
- Inspector had no way to distinguish a prepared batch from a Phase62-executed batch.

## Fixed Issues

- Added `execute_longform_chapter_batch`.
- Added confirmation and hash validation against persisted Phase61 artifacts.
- Added task payload, DAG, preflight, and chapter-state drift checks.
- Added execution evidence and progress checkpoint persistence.
- Added async static adapter support.
- Added inspector visibility for batch execution evidence.

## Remaining Boundary

The next phase should decide how to chain post-generation review tools after a successful single-chapter execution:

- quality review;
- continuity review;
- world-model proposal analysis;
- recovery if any review fails.

It should still avoid a full unattended multi-chapter runner until the single-chapter execution plus review loop is stable.
