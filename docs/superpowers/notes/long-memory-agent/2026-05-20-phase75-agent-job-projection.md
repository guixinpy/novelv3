# Phase75 Report: Agent Job Projection

## Summary

Phase75 adds a read-only Agent task queue projection tool: `inspect_agent_job_projection`.

The tool treats existing `BackgroundTask` records as Agent jobs without changing queue storage or runner behavior. It exposes a compact Agent-facing projection:

- queue summary and status counts;
- compact task rows;
- selected task details;
- control-plane metadata;
- progress and resume summary;
- bounded error preview;
- retry/recovery hints;
- linked `WritingAgentRun` references.

## Why This Matters

The goal document requires the task queue to support long-running writing automation: batch generation, review, revision, world-model backfill, retrieval maintenance, knowledge-base updates, and report generation.

Before this phase, the frontend API could inspect raw tasks, and longform batches had a specialized inspector. The Agent still lacked a generic task queue tool for deciding whether to resume, recover, inspect traces, or enqueue new work.

## Changes

- Added `backend/app/services/writing_agent/agent_job_projection.py`.
- Added `inspect_agent_job_projection` to the Writing Agent tool registry.
- Added executor adapter `_inspect_agent_job_projection`.
- Added service-level tests:
  - empty queue projection;
  - active generate task with control plane and progress;
  - failed task with recovery hint.
- Added registry and executor tests.

## Result Contract

Empty queue:

```json
{
  "queue": {
    "depth": 0,
    "active": 0,
    "terminal": 0
  },
  "recommended_tools": ["plan_longform_chapter_batch"]
}
```

Active selected task:

```json
{
  "selected_task": {
    "task_type": "generate_chapter",
    "status": "running",
    "control_plane": {
      "source": "writing_start"
    },
    "progress": {
      "next_chapter_index": 4
    },
    "resume": {
      "can_resume": true,
      "pending_chapter_indexes": [4, 5]
    }
  },
  "recommended_tools": ["inspect_agent_trace_audit"]
}
```

Failed selected task:

```json
{
  "selected_task": {
    "status": "failed",
    "recovery": {
      "can_retry": true,
      "recommended_tools": ["inspect_agent_trace_audit", "plan_recovery_tools"]
    }
  },
  "recommended_tools": ["inspect_agent_trace_audit", "plan_recovery_tools"]
}
```

## Verification

RED before implementation:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_job_projection.py tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py -q -k "job_projection or static_adapter_names_are_report_or_agent_native_tools or lists_unhandled_internal_tools_for_migration_tracking"
```

Result before implementation: collection failed because `app.services.writing_agent.agent_job_projection` did not exist.

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_job_projection.py tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py -q -k "job_projection or static_adapter_names_are_report_or_agent_native_tools or lists_unhandled_internal_tools_for_migration_tracking"
```

Result: `8 passed, 50 deselected in 0.31s`.

Related queue/writing regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_job_projection.py tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py tests\test_background.py tests\test_writing.py -q
```

Result: `123 passed in 6.80s`.

All Writing Agent related tests:

```powershell
cd backend
$files = Get-ChildItem tests -Filter "test_writing_agent_*.py" | ForEach-Object { $_.FullName }; .venv\Scripts\python.exe -m pytest @files tests\test_athena_ontology_agent.py -q
```

Result: `225 passed in 17.45s`.

## Novel Progress

No production novel chapter was generated in this phase. This phase strengthens long-running task visibility before resuming real dogfood generation.

## Fixed Issues

- Agent lacked a generic view of background jobs.
- Task-level control-plane metadata was not available through an Agent tool.
- Failed tasks did not have a compact Agent-facing recovery projection.
- Active tasks did not expose pending chapter indexes through a generic Agent route.

## Remaining Boundary

This phase is read-only. It does not:

- retry or cancel jobs;
- change `LocalTaskRunner`;
- change task types;
- add a frontend queue view.

Recommended next phases:

1. Start the minimum Knowledge Base loop for author memory, project strategy, and self-optimization experience.
2. Resume real dogfood generation using memory route, world-model route, trace audit, and job projection as the pre-generation toolchain.
