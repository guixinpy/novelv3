# Phase59 Longform Batch Inspect Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only Writing Agent tool that lets the Agent inspect materialized longform chapter batch queue records before any batch execution is implemented.

**Architecture:** Introduce `inspect_longform_chapter_batch` as an internal read-only tool. It queries `longform_chapter_batch` background tasks for the project, returns compact queue summaries and optional selected task detail, and exposes resume/progress/readiness metadata without mutating task state.

**Tech Stack:** FastAPI backend, SQLAlchemy models, BackgroundTask, Writing Agent tool registry/executor, pytest.

---

## Reference Assimilation

Initial Phase59 translation:

- `openclaw`: task ledgers must expose current status, checkpoint/progress, resumability, and pending handoff data before execution automation.
- `hermes-agent`: queue visibility should include idempotency key, created/updated timing, active status, and stale/retry signals.
- `openhuman`: compact projections should show last seen/checkpoint and escalation state without forcing callers to load heavy payloads.
- novelv3 current queue: `BackgroundTask` already stores `payload`, `result`, `status`, timestamps, and compact progress for range tasks.

Phase59 adaptation:

- Add Agent tool only; do not create a new public frontend API in this phase.
- Read only `longform_chapter_batch` tasks.
- Return compact list by default and selected detail when `task_id` or `plan_hash` is provided.
- Keep output small and stable enough to feed future planner/executor tools.

## Files

- Create: `backend/app/services/writing_agent/batch_queue_inspector.py`
  - Query project-scoped `longform_chapter_batch` tasks.
  - Build compact task summaries.
  - Include selected task detail and resume/progress hints.
- Modify: `backend/app/services/writing_agent/tool_registry.py`
  - Register `inspect_longform_chapter_batch`.
- Modify: `backend/app/services/writing_agent/tool_executor.py`
  - Add static read-only adapter.
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
  - Assert descriptor and target type.
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
  - Assert adapter metadata and dispatch.
- Modify: `backend/tests/test_writing_agent_runs.py`
  - Assert API output after enqueuing a batch and when a task is missing.
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-20-phase59-longform-batch-inspect.md`
  - Record implementation, reference absorption, verification, and next phase.

## Task 1: RED for Tool Contract

- [x] **Step 1: Add failing registry and executor tests**

Expected descriptor:

```python
descriptor = get_agent_tool_descriptor("inspect_longform_chapter_batch")
assert descriptor.internal is True
assert descriptor.non_blocking_report is True
assert descriptor.category == "task_queue"
assert descriptor.target_type == "background_task"
```

Expected adapter metadata:

```python
assert writing_agent_tool_adapter_metadata("inspect_longform_chapter_batch") == {
    "tool_name": "inspect_longform_chapter_batch",
    "adapter_type": "static",
    "category": "task_queue",
    "mutability": "read",
    "handler_name": "_inspect_longform_chapter_batch",
}
```

- [x] **Step 2: Run RED**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py -q -k "longform_chapter_batch"
```

Expected: fail because `inspect_longform_chapter_batch` is not registered.

## Task 2: RED for API Behavior

- [x] **Step 1: Add failing API tests**

Ready list/detail after enqueue:

```python
enqueue_output = client.post(... enqueue confirmed ...).json()["steps"][0]["output"]
task_id = enqueue_output["task"]["id"]
response = client.post(
    f"/api/v1/projects/{project.id}/agent-runs",
    json={
        "goal": "查看长篇批次队列",
        "tools": [{"tool_name": "inspect_longform_chapter_batch", "params": {"task_id": task_id}}],
    },
)
output = response.json()["steps"][0]["output"]
assert output["status"] == "completed"
assert output["summary"]["total"] == 1
assert output["selected_task"]["id"] == task_id
assert output["selected_task"]["batch"]["chapter_indexes"] == [2, 3]
assert output["selected_task"]["execution_readiness"]["status"] == "materialized_only"
assert output["selected_task"]["resume"]["can_resume"] is False
```

Missing selected task:

```python
response = client.post(
    f"/api/v1/projects/{project.id}/agent-runs",
    json={
        "goal": "查看不存在的批次",
        "tools": [{"tool_name": "inspect_longform_chapter_batch", "params": {"task_id": "missing"}}],
    },
)
output = response.json()["steps"][0]["output"]
assert output["status"] == "not_found"
assert output["summary"]["total"] == 0
```

- [x] **Step 2: Run RED**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "inspect_longform_chapter_batch"
```

Expected: fail because the tool is unsupported.

## Task 3: GREEN Implementation

- [x] **Step 1: Implement inspector module**

Create `inspect_longform_chapter_batch_queue(db, project_id, task_id=None, plan_hash=None, limit=None)`.

Rules:

- clamp `limit` to `1..20`, default `10`;
- filter by `project_id` and `task_type="longform_chapter_batch"`;
- optional selected task by project-scoped `task_id`;
- optional selected task by `payload.plan_hash`;
- return `status="not_found"` only when a selector was provided and no selected task exists;
- include compact task list with id, status, chapter range, plan hash, queue policy, timestamps;
- selected detail includes batch, DAG summary, tools, progress, resume, execution readiness.

- [x] **Step 2: Register and adapt tool**

Add descriptor and static adapter.

- [x] **Step 3: Run focused GREEN**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py -q -k "longform_chapter_batch"
```

Expected: pass.

## Task 4: Verification and Report

- [x] **Step 1: Run T1 Agent and queue verification**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_writing_agent_planner.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_tool_registry.py tests\test_background.py -q
```

- [x] **Step 2: Run static checks**

Run:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

- [x] **Step 3: Write phase report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-20-phase59-longform-batch-inspect.md`.

- [x] **Step 4: Commit and push**

Run:

```powershell
git status --short
git add backend docs
git commit -m "feat: inspect longform chapter batches"
git push origin main
```
