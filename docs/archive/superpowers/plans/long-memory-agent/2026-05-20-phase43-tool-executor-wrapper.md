# Phase43 Tool Executor Wrapper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or a targeted local TDD loop. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Start separating Writing Agent tool execution from `run_service.py` by introducing a registry-backed executor wrapper for Agent-native tools and standardizing failed/blocked step outputs even when no tool output exists.

**Architecture:** Keep `WritingAgentRunService` responsible for run lifecycle, step persistence, stop/block decisions, and chapter-specific enrichment. Add a small `tool_executor.py` layer that can execute Agent-native internal tools through a typed context and explicit handled/unhandled result. This creates the seam for later Athena/Hermes/Knowledge Base tools to move behind stable adapters without rewriting the full run engine in one phase.

**Tech Stack:** Pydantic request schema, SQLAlchemy session context, Writing Agent registry/planner/run service, targeted pytest.

---

## Why This Phase

Phase40-42 added a tool registry, deterministic planner, and step-level result envelope. The remaining bottleneck is that `_execute_tool` is still a large dispatcher inside `run_service.py`.

This phase makes the next Agent architecture step concrete:

- Agent-native tools can be executed by a dedicated executor layer.
- `run_service.py` can delegate before falling back to the existing execution path.
- Future module toolization can move tool-by-tool instead of through a high-risk rewrite.
- Failed or blocked steps will always have a normalized `agent_tool_result` envelope, giving recovery logic a stable shape.

## Scope

In scope:

- Add `backend/app/services/writing_agent/tool_executor.py`.
- Move execution of `describe_agent_tools`, `plan_writing_agent_run`, and `preflight_writing` into the executor wrapper.
- Keep `generate_chapter`, async action-service tools, revision tools, and world-model mutation tools in `run_service.py` for now.
- Add tests for executor handled/unhandled behavior.
- Add tests for failed step output normalization when an unsupported tool is rejected before execution.

Out of scope:

- Full `_execute_tool` decomposition.
- Retry or recovery policy engine.
- New database tables or migrations.
- Frontend changes.
- Large-scale chapter generation.

## Task 1: Write Failing Tests

**Files:**

- Add: `backend/tests/test_writing_agent_tool_executor.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Test executor handles Agent-native tools**

Add tests proving:

- `describe_agent_tools` returns handled output with `status == "completed"`;
- `plan_writing_agent_run` returns handled output with planner `steps`;
- `preflight_writing` can be handled through an injected callback.

- [x] **Step 2: Test executor leaves legacy tools untouched**

Add a test proving `generate_setup` or `generate_chapter` returns `handled is False`, so `run_service.py` can still delegate to the existing action path.

- [x] **Step 3: Test unsupported tool failure has normalized output**

In `test_writing_agent_runs.py`, add an API test for an unsupported tool and assert the failed step output includes:

- `status == "failed"`;
- `error`;
- `agent_tool_result.version`;
- `agent_tool_result.step_status == "failed"`;
- `agent_tool_result.is_error is True`.

- [x] **Step 4: Verify red**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py -q -k "tool_executor or unsupported_tool"
```

Expected: FAIL because the executor module and normalized unsupported output do not exist yet.

## Task 2: Implement Executor Wrapper

**Files:**

- Add: `backend/app/services/writing_agent/tool_executor.py`
- Modify: `backend/app/services/writing_agent/run_service.py`

- [x] **Step 1: Add execution context and result type**

Create:

```python
@dataclass(frozen=True)
class WritingAgentToolContext:
    db: Session
    project_id: str
    run_id: str | None = None

@dataclass(frozen=True)
class WritingAgentToolExecutionResult:
    handled: bool
    output: dict[str, Any] | None = None
```

- [x] **Step 2: Add `execute_writing_agent_tool`**

Support:

- `describe_agent_tools`;
- `plan_writing_agent_run`;
- `preflight_writing` via injected `preflight_writing` callable.

Unknown or legacy tools return `handled=False`.

- [x] **Step 3: Delegate from `run_service.py`**

At the start of `_execute_tool`, call the executor. If handled, return its output. Otherwise continue through the existing code path.

## Task 3: Normalize Missing Failure/Block Outputs

**Files:**

- Modify: `backend/app/services/writing_agent/run_service.py`

- [x] **Step 1: Add fallback output for failed steps**

If `_fail_step_and_run(..., output=None)` is called, store:

```python
{"status": "failed", "error": error}
```

then attach `agent_tool_result`.

- [x] **Step 2: Add fallback output for blocked steps**

If `_block_step_and_run(..., output=None)` is called, store:

```python
{"status": "blocked", "error": error}
```

then attach `agent_tool_result`.

## Task 4: Verify and Report

**Files:**

- Modify: this plan checklist.
- Add: `docs/superpowers/notes/long-memory-agent/2026-05-20-phase43-tool-executor-wrapper.md`

- [x] **Step 1: Run T1 verification**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py tests\test_writing_agent_planner.py tests\test_writing_agent_tool_registry.py -q
```

- [x] **Step 2: Run static diff check**

Run:

```powershell
git diff --check
```

- [x] **Step 3: Write phase report**

Record:

- changes;
- verification evidence;
- why this serves long-form Agent stability;
- next recommended phase.

- [x] **Step 4: Commit**

Commit code and docs if verification passes.
