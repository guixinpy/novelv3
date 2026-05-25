# Phase57 Longform Batch Plan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only Writing Agent tool that proposes a bounded longform chapter batch DAG from current project state and optional continuation state.

**Architecture:** Introduce `plan_longform_chapter_batch` as an internal read-only tool. It does not enqueue or execute work. It returns a bounded DAG with chapter window, tool phases, dependencies, acceptance criteria, and recovery/continuation hints. If a source run is blocked or failed, the batch plan refuses to continue generation and points to recovery first.

**Tech Stack:** FastAPI backend, SQLAlchemy models, Writing Agent tool registry/executor, pytest.

---

## Reference Assimilation

Explorer results are running in parallel and will be folded into the phase report. Initial translation:

- `openclaw`: batch planning should be a continuation route from canonical run state, not a UI-only checklist.
- `hermes-agent`: after handoff or compaction, the next plan should name the next concrete tool action, not just an acknowledgement.
- `openhuman`: bounded DAG nodes need dependencies and acceptance criteria; keep the first version small and auditable.

novelv3 adaptation:

- The tool is read-only and returns a plan, not a queue job.
- The DAG uses broad phase nodes so node count stays bounded.
- The plan consumes `continuation_state` when `source_run_id` is provided.
- Blocked source runs must recover before planning further generation.

## Files

- Create: `backend/app/services/writing_agent/batch_planner.py`
  - Build read-only chapter batch DAG.
  - Infer chapter window from explicit params, source continuation state, or latest generated chapter.
  - Block planning when source continuation state is blocked/failed.
- Modify: `backend/app/services/writing_agent/tool_registry.py`
  - Register `plan_longform_chapter_batch`.
- Modify: `backend/app/services/writing_agent/tool_executor.py`
  - Add static read-only adapter.
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
  - Assert descriptor and target type.
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
  - Assert adapter metadata and dispatch.
- Modify: `backend/tests/test_writing_agent_runs.py`
  - Assert API output for ready batch planning and blocked source-run planning.
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-20-phase57-longform-batch-plan.md`
  - Record implementation, reference absorption, verification, and next phase.

## Task 1: RED for Tool Contract

- [x] **Step 1: Add failing registry and executor tests**

Expected descriptor:

```python
descriptor = get_agent_tool_descriptor("plan_longform_chapter_batch")
assert descriptor.internal is True
assert descriptor.non_blocking_report is True
assert descriptor.category == "task_queue"
assert descriptor.target_type == "longform_batch_plan"
```

Expected adapter metadata:

```python
assert writing_agent_tool_adapter_metadata("plan_longform_chapter_batch") == {
    "tool_name": "plan_longform_chapter_batch",
    "adapter_type": "static",
    "category": "task_queue",
    "mutability": "read",
    "handler_name": "_plan_longform_chapter_batch",
}
```

- [x] **Step 2: Run RED**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py -q -k "longform_chapter_batch"
```

Expected: fail because the tool is not registered.

## Task 2: RED for API Behavior

- [x] **Step 1: Add failing API tests**

Add one ready planning test:

```python
response = client.post(
    f"/api/v1/projects/{project.id}/agent-runs",
    json={
        "goal": "规划接下来两章的批次任务",
        "tools": [{"tool_name": "plan_longform_chapter_batch", "params": {"start_chapter": 2, "batch_size": 2}}],
    },
)
output = response.json()["steps"][0]["output"]
assert output["status"] == "completed"
assert output["batch"]["chapter_indexes"] == [2, 3]
assert output["dag"]["node_count"] <= 8
assert [node["node_id"] for node in output["dag"]["nodes"]] == [
    "context_diagnostics",
    "preflight_gate",
    "chapter_generation",
    "quality_review",
    "continuity_review",
    "world_model_intake",
    "batch_checkpoint",
]
assert output["dag"]["nodes"][2]["tool_name"] == "generate_chapter"
assert output["dag"]["nodes"][2]["depends_on"] == ["preflight_gate"]
```

Add one blocked source-run test:

```python
blocked = client.post(... auto_plan chapter 2 ...)
response = client.post(
    f"/api/v1/projects/{project.id}/agent-runs",
    json={
        "goal": "从阻塞运行规划批次",
        "tools": [{"tool_name": "plan_longform_chapter_batch", "params": {"source_run_id": blocked.json()["id"]}}],
    },
)
output = response.json()["steps"][0]["output"]
assert output["status"] == "blocked"
assert output["recommended_next_tools"] == ["plan_recovery_tools"]
assert output["source_continuation_state"]["status"] == "blocked"
```

- [x] **Step 2: Run RED**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "longform_batch"
```

Expected: fail because the tool is unsupported.

## Task 3: GREEN Implementation

- [x] **Step 1: Implement batch planner module**

Create `build_longform_chapter_batch_plan(db, project_id, source_run_id=None, start_chapter=None, batch_size=None)`.

Rules:

- default `batch_size=1`;
- clamp `batch_size` to `1..3`;
- if `source_run_id` has `continuation_state.status in {"blocked", "failed"}`, return blocked plan with `recommended_next_tools=["plan_recovery_tools"]`;
- if source is completed and no explicit start chapter, use `target_chapter_index + 1`;
- else infer latest generated chapter + 1;
- DAG node count must be bounded at 7 nodes.

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
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_writing_agent_planner.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_tool_registry.py -q
```

- [x] **Step 2: Run static checks**

Run:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

- [x] **Step 3: Write phase report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-20-phase57-longform-batch-plan.md`.

- [x] **Step 4: Commit and push**

Run:

```powershell
git status --short
git add backend docs
git commit -m "feat: plan longform chapter batches"
git push origin main
```
