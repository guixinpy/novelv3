# Phase58 Report: Longform Batch Enqueue

## Summary

Phase58 added `enqueue_longform_chapter_batch`, a guarded Writing Agent tool that converts a Phase57 longform batch plan into a resumable background task record.

The tool is intentionally two-step:

- preview by default, with `confirmation_required` and a stable `plan_hash`;
- confirmed enqueue only when `confirm_enqueue=true` and the submitted hash matches the server-recomputed plan.

This phase does not start real generation. It materializes the task ledger entry only, so later phases can build execution, checkpointing, resume, and review loops on top.

## Reference Assimilation

Subagent reference review confirmed that Phase58 should absorb:

- `openclaw`: separate task ledger from recoverable flow execution; store resumable state explicitly.
- `hermes-agent`: use structured preview, explicit confirmation, idempotency, and stale-plan protection.
- `openhuman`: high-risk side effects need confirmation; background work should carry logs/checkpoints and not silently mutate content.

Not adopted:

- generic Kanban product surface;
- multi-runtime worker pools;
- automatic background writing;
- third-party task-flow dependencies.

novelv3 adaptation:

- one domain-specific task type: `longform_chapter_batch`;
- plan hash is server computed;
- task payload stores batch, DAG, tool requests, queue policy, and hash payload;
- idempotency reuses an active matching task;
- materialized tasks do not start `LocalTaskRunner` in this phase.

## Changes

- Added `backend/app/services/writing_agent/batch_enqueue.py`.
- Registered `enqueue_longform_chapter_batch` as an internal write tool.
- Added static executor adapter metadata and dispatch.
- Added API tests for preview, hash mismatch, confirmed enqueue, duplicate confirmation, and blocked source runs.
- Added a background task regression test to keep materialized queue items from being failed during restart cleanup.
- Updated `BackgroundTaskService.fail_interrupted_running_tasks()` to exclude tasks whose payload declares `queue_policy.starts_runner=false`.

## Tool Contract

Preview output:

- `status: "confirmation_required"`;
- `preview_only: true`;
- `can_enqueue: true`;
- stable `plan_hash`;
- `required_confirmation.confirm_enqueue: true`;
- batch and DAG copied from the server-side Phase57 plan;
- `queue_policy.starts_runner: false`.

Hash mismatch output:

- `status: "hash_mismatch"`;
- `can_enqueue: false`;
- `provided_plan_hash`;
- `expected_plan_hash`;
- no background task is created.

Confirmed enqueue output:

- `status: "queued"`;
- `preview_only: false`;
- `task.task_type: "longform_chapter_batch"`;
- `task.status: "pending"`;
- task payload contains `plan_hash`, `batch`, `dag`, `tools`, `hash_payload`, and `queue_policy`.

Blocked source output:

- preserves the Phase57 blocked status;
- `can_enqueue: false`;
- recommends recovery first;
- does not create a task.

## Verification

RED registry/executor:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py -q -k "longform_chapter_batch"
```

Result before implementation: `3 failed, 3 passed, 19 deselected`.

RED API:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "enqueue_longform_chapter_batch"
```

Initial selector missed the new test names; the corrected RED path was covered by the focused GREEN selector after implementation. The failing behavior before implementation was unsupported tool/descriptor absence.

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py -q -k "longform_chapter_batch"
```

Result: `12 passed, 148 deselected in 0.68s`.

Restart cleanup regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_background.py -q -k "materialized_queue_items or interrupted"
```

Result: `6 passed, 29 deselected in 0.34s`.

T1 Agent and queue verification:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_writing_agent_planner.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_tool_registry.py tests\test_background.py -q
```

Result: `199 passed in 12.59s`.

## Novel Progress

No new chapter was generated. This phase is infrastructure for safe multi-chapter execution. It improves the system's ability to support longform generation without relying on a single synchronous request.

## Discovered Issues

- Materialized batch tasks would have been marked failed by restart cleanup because they used `pending` status without a runner.

## Fixed Issues

- `BackgroundTaskService.fail_interrupted_running_tasks()` now excludes materialized queue items with `queue_policy.starts_runner=false`.

## Remaining Boundary

The queued task is not executable yet. It is a durable task record with plan payload. Later phases still need:

- a batch worker/executor;
- checkpointed node execution;
- per-node review/world-model handoff;
- resume from task progress;
- compact task list/detail projection for frontend visibility.

## Next Phase Recommendation

Phase59 should add a read-only queue status/detail tool for `longform_chapter_batch`, so the Agent can inspect queued batches before implementing execution. This keeps queue observability ahead of queue automation.
