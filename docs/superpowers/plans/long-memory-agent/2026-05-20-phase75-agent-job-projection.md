# Agent Job Projection Phase75 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only Agent job projection tool that summarizes background tasks as Agent jobs with control-plane metadata, progress, recovery hints, and linked Agent run references.

**Architecture:** Keep `BackgroundTask` and existing queue semantics unchanged. Add a compact projection service in the Writing Agent layer that reads existing tasks and returns Agent-facing job status. Register it as an internal, read-only, non-blocking task-queue tool so future Agent planning can inspect long-running jobs before deciding resume/retry/recover actions.

**Tech Stack:** SQLAlchemy models, BackgroundTaskService conventions, Writing Agent tool registry/executor, pytest.

---

## Context

The long-term goal requires task queue support for long-running creation workflows. Recent phases added:

- writing task `control_plane` metadata;
- Agent memory route;
- Agent trace audit;
- Agent world-model route.

The missing queue-level piece is a generic Agent view of `BackgroundTask` records. Existing APIs expose raw task detail or a longform-batch-specific inspector, but the Agent still lacks one generic tool to inspect active/completed/failed jobs and decide what to do next.

## Files

- Create `backend/app/services/writing_agent/agent_job_projection.py`.
- Modify `backend/app/services/writing_agent/tool_registry.py`.
- Modify `backend/app/services/writing_agent/tool_executor.py`.
- Add `backend/tests/test_writing_agent_job_projection.py`.
- Modify `backend/tests/test_writing_agent_tool_registry.py`.
- Modify `backend/tests/test_writing_agent_tool_executor.py`.
- Add Phase75 report under `docs/superpowers/notes/long-memory-agent/`.

## Task 1: RED Registry And Executor Tests

- [ ] Add `inspect_agent_job_projection` to expected tool names.
- [ ] Assert:

```python
assert target_type_for_tool("inspect_agent_job_projection") == "agent_job_projection"
assert "inspect_agent_job_projection" in non_blocking_report_tool_names()
```

- [ ] Add executor adapter metadata expectation:

```python
assert writing_agent_tool_adapter_metadata("inspect_agent_job_projection") == {
    "tool_name": "inspect_agent_job_projection",
    "adapter_type": "static",
    "category": "task_queue",
    "mutability": "read",
    "handler_name": "_inspect_agent_job_projection",
}
```

## Task 2: Service Tests

- [ ] Empty queue:
  - project with no background tasks;
  - output status `completed`;
  - queue depth 0;
  - recommended tool includes `plan_longform_chapter_batch`.
- [ ] Active generate task:
  - task has `payload.control_plane`, `chapter_range`, and `result.progress`;
  - selected task exposes control plane, progress, resume summary, and pending chapters.
- [ ] Failed task:
  - task status failed with error;
  - projection exposes bounded error preview;
  - recovery `can_retry` true;
  - recommended tools include `inspect_agent_trace_audit` and `plan_recovery_tools`.

## Task 3: Implementation

- [ ] Create:

```python
def inspect_agent_job_projection(
    db: Session,
    project_id: str,
    *,
    task_id: str | None = None,
    task_type: str | None = None,
    status: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
```

- [ ] Query by project, optional task id/type/status.
- [ ] Return:
  - queue summary and status counts;
  - compact tasks;
  - selected task when `task_id` is provided;
  - control plane from task payload;
  - progress/resume summary;
  - linked Agent run references by `background_task_id`;
  - recommended tools.
- [ ] Keep output compact and JSON-safe.

## Task 4: Verification

- [ ] Focused:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_job_projection.py tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py -q -k "job_projection or static_adapter_names_are_report_or_agent_native_tools or lists_unhandled_internal_tools_for_migration_tracking"
```

- [ ] Related:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_job_projection.py tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py tests\test_background.py tests\test_writing.py -q
```

- [ ] Static checks:

```powershell
git diff --check
rg -l "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

## Boundaries

Do:

- keep the tool read-only;
- preserve existing task API and task service behavior;
- summarize control plane/progress/recovery compactly;
- expose linked Agent run IDs when available.

Do not:

- implement retry/cancel/resume mutations;
- change LocalTaskRunner;
- change existing task types;
- add frontend UI in this phase.
