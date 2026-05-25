# Phase60 Report: Longform Batch Preflight Checkpoint

## Summary

Phase60 added `execute_longform_chapter_batch_preflight`, an internal Writing Agent tool that performs a controlled preflight handoff for materialized `longform_chapter_batch` tasks.

The tool validates a queued task, runs safe chapter preflight checks, writes a bounded checkpoint into `BackgroundTask.result`, and stops before `chapter_generation`.

No prose generation, runner start, world model mutation, review mutation, or longform memory repair is executed in this phase.

## Reference Assimilation

Adopted:

- `openclaw`: canonical execution plan binding through task id, plan hash, chapter range, DAG node ids, and explicit skipped actions.
- `hermes-agent`: incremental checkpoint discipline via `preflight_checkpoint` plus bounded `execution_checkpoints`.
- `openhuman`: preflight/evidence handoff shape through gates, required confirmation, execution policy, side effects, and expected evidence.

Not adopted:

- host command/sandbox execution systems;
- generic connector/phone approval flows;
- LLM-based approval;
- full attempt table, heartbeat, retry worker, or queue claim semantics.

## Changes

- Added `backend/app/services/writing_agent/batch_preflight.py`.
- Registered `execute_longform_chapter_batch_preflight` as an internal `task_queue` write tool.
- Added executor adapter metadata and dispatch for the new tool.
- Extended `inspect_longform_chapter_batch` detail output with:
  - `preflight_checkpoint`;
  - `execution_checkpoints`.
- Added registry, executor, and API tests for ready and blocked preflight scenarios.

## Tool Contract

Input:

- `task_id` required;
- `max_chapters` optional, clamped to a small bounded range.

Ready output includes:

- `status: "ready"`;
- selected task metadata;
- `canonical_execution_plan`;
- `checkpoint`;
- `gates`;
- `resume`;
- `execution_policy`;
- `required_confirmation`;
- `side_effects`;
- `expected_evidence`;
- `recommended_next_tools`.

Blocked output uses `status: "blocked"` so the Writing Agent run halts normally and records the blocker.

Side effect boundary:

- executed: `background_task_result_checkpoint`;
- skipped: `start_runner`, `generate_chapter`, `world_model_apply`;
- blocked high risk: `chapter_generation`, `world_model_intake`.

## Verification

RED focused tests:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py -q -k "execute_longform_chapter_batch_preflight or preflight_longform_chapter_batch"
```

Result before implementation: `5 failed, 165 deselected`.

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py -q -k "execute_longform_chapter_batch_preflight or preflight_longform_chapter_batch"
```

Result: `5 passed, 165 deselected in 0.84s`.

Batch chain regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py -q -k "longform_chapter_batch"
```

Result: `22 passed, 148 deselected in 1.07s`.

T1 related regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_writing_agent_planner.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_tool_registry.py tests\test_background.py -q
```

Result: `209 passed in 12.99s`.

Static checks:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

Result:

- `git diff --check` passed; it reported only the existing line-ending normalization warning for `backend/tests/test_writing_agent_runs.py`.
- secret scan returned no matches.

## Novel Progress

No new novel chapter was generated. This phase intentionally improves the Agent task execution substrate before real longform batch generation resumes.

## Discovered Issues

- The queued batch system had no safe execution handoff between materialization and future generation.
- The inspector did not expose task-level execution checkpoints.

## Fixed Issues

- Added a deterministic preflight checkpoint tool for queued longform batches.
- Added durable checkpoint history to task result.
- Added inspector visibility for preflight checkpoints.
- Added regression tests to ensure the tool does not create chapter content.

## Remaining Boundary

The system still does not have a real batch executor. The next phase should add an explicit confirmation/approval contract or attempt model before any runner is allowed to call `generate_chapter`.

Recommended next phase:

- add `execute_longform_chapter_batch` as a confirmation-only preview first, or
- add a batch attempt table/checkpoint manifest before implementing actual generation.
