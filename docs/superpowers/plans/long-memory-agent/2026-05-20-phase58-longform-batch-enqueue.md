# Phase58 Longform Batch Enqueue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a guarded Writing Agent tool that converts a Phase57 longform batch plan into a resumable background task record after explicit hash confirmation.

**Architecture:** Introduce `enqueue_longform_chapter_batch` as an internal write tool. It reuses the deterministic Phase57 planner, returns a preview with `plan_hash` by default, requires `confirm_enqueue=true` and matching `plan_hash` before creating a background task, and stores the batch DAG in task payload without starting real generation yet.

**Tech Stack:** FastAPI backend, SQLAlchemy models, BackgroundTaskService, Writing Agent tool registry/executor, pytest.

---

## Reference Assimilation

Initial translation from the three reference projects and current novelv3 queue boundary:

- `openclaw`: enqueue must be resumable from explicit serialized state, not hidden process memory.
- `hermes-agent`: preview and execution need a stable hash so stale plans cannot be executed blindly.
- `openhuman`: queue task payload should carry ownership, acceptance criteria, and validation metadata for later task-board style execution.
- novelv3 current task system: `BackgroundTaskService.create_chapter_range()` already supports chapter ranges, progress, retry checkpoints, and idempotency keys.

Phase58 adaptation:

- Use `BackgroundTaskService.create_chapter_range()` with a dedicated task type `longform_chapter_batch`.
- Store the Phase57 DAG and execution metadata in task payload.
- Do not call `LocalTaskRunner` in this phase.
- Reuse active tasks by idempotency key.
- Block enqueue when the Phase57 plan is blocked or failed.

## Files

- Create: `backend/app/services/writing_agent/batch_enqueue.py`
  - Build preview from `build_longform_chapter_batch_plan`.
  - Compute stable `plan_hash`.
  - Require confirmation before task creation.
  - Create idempotent background task payload when confirmed.
- Modify: `backend/app/services/writing_agent/tool_registry.py`
  - Register `enqueue_longform_chapter_batch`.
- Modify: `backend/app/services/writing_agent/tool_executor.py`
  - Add static write adapter.
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
  - Assert descriptor and target type.
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
  - Assert adapter metadata and dispatch.
- Modify: `backend/tests/test_writing_agent_runs.py`
  - Assert preview, hash mismatch, confirmed enqueue, blocked source-run behavior.
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-20-phase58-longform-batch-enqueue.md`
  - Record implementation, reference absorption, verification, and next phase.

## Task 1: RED for Tool Contract

- [x] **Step 1: Add failing registry and executor tests**

Expected descriptor:

```python
descriptor = get_agent_tool_descriptor("enqueue_longform_chapter_batch")
assert descriptor.internal is True
assert descriptor.category == "task_queue"
assert descriptor.target_type == "background_task"
```

Expected adapter metadata:

```python
assert writing_agent_tool_adapter_metadata("enqueue_longform_chapter_batch") == {
    "tool_name": "enqueue_longform_chapter_batch",
    "adapter_type": "static",
    "category": "task_queue",
    "mutability": "write",
    "handler_name": "_enqueue_longform_chapter_batch",
}
```

- [x] **Step 2: Run RED**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py -q -k "longform_chapter_batch"
```

Expected: fail because `enqueue_longform_chapter_batch` is not registered.

## Task 2: RED for API Behavior

- [x] **Step 1: Add failing API tests**

Preview without confirmation:

```python
response = client.post(
    f"/api/v1/projects/{project.id}/agent-runs",
    json={
        "goal": "准备把接下来两章加入批次队列",
        "tools": [{"tool_name": "enqueue_longform_chapter_batch", "params": {"start_chapter": 2, "batch_size": 2}}],
    },
)
output = response.json()["steps"][0]["output"]
assert output["status"] == "confirmation_required"
assert output["preview_only"] is True
assert output["can_enqueue"] is True
assert output["plan_hash"]
assert output["required_confirmation"] == {"confirm_enqueue": True, "plan_hash": output["plan_hash"]}
assert output["batch"]["chapter_indexes"] == [2, 3]
```

Hash mismatch:

```python
response = client.post(
    f"/api/v1/projects/{project.id}/agent-runs",
    json={
        "goal": "尝试执行过期批次计划",
        "tools": [{
            "tool_name": "enqueue_longform_chapter_batch",
            "params": {"start_chapter": 2, "batch_size": 2, "confirm_enqueue": True, "plan_hash": "stale"},
        }],
    },
)
assert response.json()["steps"][0]["output"]["status"] == "hash_mismatch"
```

Confirmed enqueue:

```python
preview = client.post(...).json()["steps"][0]["output"]
response = client.post(
    f"/api/v1/projects/{project.id}/agent-runs",
    json={
        "goal": "确认加入批次队列",
        "tools": [{
            "tool_name": "enqueue_longform_chapter_batch",
            "params": {
                "start_chapter": 2,
                "batch_size": 2,
                "confirm_enqueue": True,
                "plan_hash": preview["plan_hash"],
            },
        }],
    },
)
output = response.json()["steps"][0]["output"]
assert output["status"] == "queued"
assert output["task"]["task_type"] == "longform_chapter_batch"
assert output["task"]["status"] == "pending"
assert output["task"]["chapter_range"] == {"start": 2, "end": 3}
assert output["batch"]["chapter_indexes"] == [2, 3]
```

- [x] **Step 2: Run RED**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "enqueue_longform_chapter_batch"
```

Expected: fail because the tool is unsupported.

## Task 3: GREEN Implementation

- [x] **Step 1: Implement enqueue module**

Create `build_longform_chapter_batch_enqueue(db, project_id, source_run_id=None, start_chapter=None, batch_size=None, confirm_enqueue=False, plan_hash=None)`.

Rules:

- call `build_longform_chapter_batch_plan()` first;
- if plan status is `blocked` or `failed`, return the plan status with `can_enqueue=false`;
- compute stable `plan_hash` from plan version, project id, source run id, batch, DAG node ids, and tool requests;
- if not confirmed, return `confirmation_required`;
- if confirmed hash does not match, return `hash_mismatch`;
- create `BackgroundTaskService.create_chapter_range()` with:
  - `task_type="longform_chapter_batch"`;
  - `chapter_range` from batch start/end;
  - idempotency key `longform_batch:{project_id}:{start}:{end}:{plan_hash}`;
  - payload containing `plan_hash`, `batch`, `dag`, `tools`, `source_run_id`, `queue_policy`.

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

- [x] **Step 1: Run T1 Agent verification**

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

Create `docs/superpowers/notes/long-memory-agent/2026-05-20-phase58-longform-batch-enqueue.md`.

- [x] **Step 4: Commit and push**

Run:

```powershell
git status --short
git add backend docs
git commit -m "feat: enqueue longform chapter batches"
git push origin main
```
