# Phase42 Agent Step Trace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make planner-derived Writing Agent executions traceable at step level by carrying planner metadata into each tool request and attaching a normalized result envelope to step outputs.

**Architecture:** Extend `WritingAgentToolRequest` with optional planner metadata. `planner.py` writes step reason/failure policy/expected output into each generated request without polluting tool params. `run_service.py` persists that metadata in `WritingAgentStep.input` and adds a compact `agent_tool_result` envelope to completed/blocked/failed step outputs.

**Tech Stack:** Pydantic schemas, SQLAlchemy JSON fields, Writing Agent planner/run service, targeted pytest.

---

## Why This Phase

Phase41 can generate and execute a bounded tool chain, but the run detail still makes downstream analysis work harder:

- step input stores only `command_args` and `params`;
- planner reasons and failure policies are only in the original plan object;
- output shape is tool-specific, so quality/recovery logic must inspect many ad hoc formats.

This phase adds a minimal trace layer without database migration.

## Scope

In scope:

- Add optional `planner` metadata field to `WritingAgentToolRequest`.
- Add planner metadata to planner-produced `tools`.
- Persist planner metadata into `WritingAgentStep.input`.
- Add `agent_tool_result` envelope to step outputs.
- Cover auto-planned run detail with tests.

Out of scope:

- New database tables.
- Full event stream / task board.
- Retry engine.
- Splitting `_execute_tool` into executor objects.
- Frontend UI changes.

## Envelope Contract

Each successful or blocked/failed step output should include:

```python
"agent_tool_result": {
    "version": "phase42.tool_result.v1",
    "tool_name": "generate_chapter",
    "step_index": 3,
    "step_status": "success",
    "result_status": "success",
    "is_error": False,
    "trace_id": "trace-chapter-2",
    "planner": {
        "reason": "依赖满足后生成第2章正文。",
        "on_missing": "stop",
        "on_failure": "stop",
        "expected_output": "章节正文。",
        "post_generation": False
    },
    "output_keys": ["chapter_index", "status", "trace_id"]
}
```

## Task 1: Write Failing Tests

**Files:**

- Modify: `backend/tests/test_writing_agent_planner.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Test planner tools carry metadata**

In `test_planner_builds_ready_next_chapter_tool_chain`, assert the `generate_chapter` tool request contains:

```python
{
    "planner": {
        "reason": "依赖满足后生成第2章正文。",
        "on_missing": "stop",
        "on_failure": "stop",
        "expected_output": "章节正文。",
        "post_generation": False,
    }
}
```

Also assert the post-generation review tool has `planner["post_generation"] is True`.

- [x] **Step 2: Test auto-planned run persists planner metadata and result envelope**

In `test_agent_run_auto_plan_executes_high_level_next_chapter_goal`, assert:

- `generate_chapter` step input includes `planner.reason`;
- `generate_chapter` output includes `agent_tool_result`;
- envelope has `tool_name`, `step_status`, `result_status`, `is_error`, `planner.reason`, and `trace_id`;
- post-generation step input keeps `planner.post_generation is True`.

- [x] **Step 3: Verify red**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_planner.py tests\test_writing_agent_runs.py -q -k "ready_next_chapter_tool_chain or auto_plan_executes"
```

Expected: FAIL because planner metadata and result envelope are not implemented yet.

## Task 2: Implement Planner Metadata

**Files:**

- Modify: `backend/app/schemas/writing_agent.py`
- Modify: `backend/app/services/writing_agent/planner.py`

- [x] **Step 1: Extend request schema**

Add:

```python
planner: dict[str, Any] = Field(default_factory=dict)
```

to `WritingAgentToolRequest`.

- [x] **Step 2: Add planner metadata to tool requests**

Update `_tool_request_from_step(step)` in `planner.py` to include:

```python
"planner": {
    "step_index": step["step_index"],
    "reason": step["reason"],
    "on_missing": step["on_missing"],
    "on_failure": step["on_failure"],
    "expected_output": step["expected_output"],
    "post_generation": step["post_generation"],
    "planner_version": PLANNER_VERSION,
}
```

- [x] **Step 3: Verify planner tests**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_planner.py -q
```

Expected: PASS.

## Task 3: Persist Step Metadata and Result Envelope

**Files:**

- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Persist planner metadata in step input**

Update `_start_step` so `input` includes:

```python
{
    "command_args": tool.command_args,
    "params": tool.params,
    "planner": tool.planner,
}
```

Only include `planner` when non-empty.

- [x] **Step 2: Add envelope helper**

Add:

```python
AGENT_TOOL_RESULT_VERSION = "phase42.tool_result.v1"
```

and helper:

```python
def _agent_tool_result_envelope(step, output, step_status):
    ...
```

It must not recursively include `agent_tool_result` in `output_keys`.

- [x] **Step 3: Attach envelope to success/block/failure outputs**

- `_complete_step`: add envelope to output before storing.
- `_block_step_and_run`: add envelope when output exists.
- `_fail_step_and_run`: add envelope when output exists.

- [x] **Step 4: Verify run-service focused tests**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "auto_plan_executes or plan_writing_tool_chain"
```

Expected: PASS.

## Task 4: Report and Verify

**Files:**

- Create: `docs/superpowers/notes/long-memory-agent/2026-05-20-phase42-agent-step-trace.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-20-phase42-agent-step-trace.md`

- [x] **Step 1: Write phase report**

Include:

- what changed;
- why this helps Agentization;
- validation evidence;
- limits and next phase.

- [x] **Step 2: Run T1/T2 verification**

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_planner.py tests\test_writing_agent_tool_registry.py tests\test_writing_agent_runs.py -q
```

- [x] **Step 3: Commit and push**

```powershell
git add backend/app/schemas/writing_agent.py backend/app/services/writing_agent/planner.py backend/app/services/writing_agent/run_service.py backend/tests/test_writing_agent_planner.py backend/tests/test_writing_agent_runs.py docs/superpowers/plans/long-memory-agent/2026-05-20-phase42-agent-step-trace.md docs/superpowers/notes/long-memory-agent/2026-05-20-phase42-agent-step-trace.md
git commit -m "feat: trace writing agent planned steps"
git push origin main
```

## Self-Review

- This phase directly supports the goal's Trace/audit requirement.
- It preserves current DB schema and API compatibility.
- It keeps planner metadata out of tool params.
- It creates a stable hook for future retry/recovery/task-board work.
