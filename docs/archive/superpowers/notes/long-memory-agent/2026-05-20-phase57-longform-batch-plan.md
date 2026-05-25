# Phase57 Report: Longform Batch Plan

## Summary

Phase57 added a read-only Writing Agent tool, `plan_longform_chapter_batch`, for planning bounded longform chapter batches as an auditable DAG.

The tool does not enqueue jobs or generate chapters. It converts project state plus optional `source_run_id` continuation state into a compact plan that the Agent can use before handing work to queue/execution tools in a later phase.

## Reference Assimilation

- `openclaw`: absorbed the idea that continuation/resume should be based on canonical run state, with blocked states requiring recovery before forward progress.
- `hermes-agent`: absorbed bounded dependency planning, handoff metadata, and explicit next-tool recommendations after compaction or blocked runs.
- `openhuman`: absorbed plan nodes with dependency, ownership, acceptance criteria, validation boundary, and role/task-board style status.

Not adopted in this phase:

- full external task-flow runtime;
- background worker orchestration;
- SQLite task board or CAS semantics;
- automatic multi-agent spawning;
- LLM-driven task decomposition as a dependency.

The novelv3 adaptation keeps this phase deterministic, internal, read-only, and easy to test.

## Changes

- Added `backend/app/services/writing_agent/batch_planner.py`.
- Registered `plan_longform_chapter_batch` in the Writing Agent tool registry.
- Added a static read-only executor adapter for the new tool.
- Added registry, executor, and API tests for ready batch planning.
- Added blocked-source-run behavior using `continuation_state.status in {"blocked", "failed"}`.

## Tool Contract

Ready planning returns:

- `status: "completed"`;
- `batch.start_chapter`, `batch.end_chapter`, `batch.chapter_indexes`;
- bounded 7-node DAG:
  - `context_diagnostics`;
  - `preflight_gate`;
  - `chapter_generation`;
  - `quality_review`;
  - `continuity_review`;
  - `world_model_intake`;
  - `batch_checkpoint`;
- `execution_policy.mode: "preview"`;
- `execution_policy.can_execute: false`;
- `execution_policy.requires_queue: true`;
- per-node dependencies, parallelization flag, owned artifacts, acceptance criteria, validation notes, and handoff payload.

Blocked source runs return:

- `status: "blocked"`;
- `recommended_next_tools: ["plan_recovery_tools"]`;
- original `source_continuation_state`;
- empty DAG nodes;
- `execution_policy.requires_recovery: true`.

## Verification

RED registry/executor:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py -q -k "longform_chapter_batch"
```

Result: failed before implementation because the descriptor, adapter metadata, and module were missing.

RED API:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "longform_chapter_batch"
```

Result: failed before implementation because the tool was unsupported.

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py -q -k "longform_chapter_batch"
```

Result: `5 passed, 148 deselected in 0.32s`.

T1 Agent verification:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_writing_agent_planner.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_tool_registry.py -q
```

Result: `157 passed in 10.12s`.

Static checks:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

Result: no diff whitespace errors; no API-key pattern matches.

## Novel Progress

No new novel chapter was generated in this phase. This was intentional: Phase57 is an Agent infrastructure phase that prepares bounded multi-chapter planning before execution.

## Remaining Boundary

The tool only plans. It does not:

- persist a batch job;
- reserve chapters;
- execute queue tasks;
- run generation/review tools automatically;
- merge review outputs back into world state.

## Next Phase Recommendation

Phase58 should turn this plan output into a controlled preview-to-queue bridge:

- add a queue/intake tool that accepts the Phase57 DAG shape;
- keep a recovery gate before enqueuing generation;
- preserve `continuation_state` and handoff metadata across each batch node;
- add one realistic user-flow test for "continue next N chapters" without hard-coding chapter details into the user prompt.
