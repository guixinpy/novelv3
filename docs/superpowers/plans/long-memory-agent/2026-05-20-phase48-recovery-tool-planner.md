# Phase48 Recovery Tool Planner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only `plan_recovery_tools` Writing Agent tool that turns a blocked/failed run's `agent_tool_result.recovery` into a proposed next tool chain.

**Architecture:** `recovery_policy.py` remains the source of recovery decisions. A new planner helper reads a prior run detail, finds the latest blocked/failed step with recommended recovery, and returns a plan. It does not execute the recovery tool.

---

## Why This Phase

Phase47 adds structured recovery advice, but the Agent still needs a way to inspect a blocked run and produce the next tool chain. Phase48 adds that bridge without introducing automatic retry loops.

This keeps recovery deterministic and inspectable:

```text
blocked run -> plan_recovery_tools -> proposed tools -> user/Agent chooses whether to run them
```

## Scope

In scope:

- Add `plan_recovery_tools` to the tool registry.
- Add a static executor adapter for `plan_recovery_tools`.
- Add a helper that reads a previous run and returns proposed recovery tools.
- Cover missing-outline recovery with API tests.

Out of scope:

- Automatically executing recovery tools.
- Recovery for every possible tool.
- New API endpoints.
- Frontend display.

## Task 1: Write Failing Tests

**Files:**

- Modify: `backend/tests/test_writing_agent_tool_registry.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Registry test**

Assert `plan_recovery_tools` is allowed and has `target_type == "agent_tool_plan"`.

- [x] **Step 2: API test**

Create a blocked preflight run for missing chapter outline, then create another run with:

```json
{"tool_name": "plan_recovery_tools", "params": {"run_id": "<blocked_run_id>"}}
```

Assert output:

- `status == "completed"`;
- `source_run_id == blocked_run_id`;
- `recovery.next_tool == "expand_outline_window"`;
- `tools[0].tool_name == "expand_outline_window"`;
- `tools[0].params == {"start_chapter": 3, "end_chapter": 3}`;
- step `target_type == "agent_tool_plan"`.

- [x] **Step 3: Verify red**

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_runs.py -q -k "plan_recovery_tools"
```

Expected: FAIL because the tool is not registered/implemented yet.

## Task 2: Implement Planner

**Files:**

- Add: `backend/app/services/writing_agent/recovery_planner.py`
- Modify: `backend/app/services/writing_agent/tool_registry.py`
- Modify: `backend/app/services/writing_agent/tool_executor.py`

- [x] **Step 1: Add registry descriptor**

Register `plan_recovery_tools` as internal, non-blocking report, target `agent_tool_plan`.

- [x] **Step 2: Add recovery planner helper**

Find the latest blocked/failed step with `agent_tool_result.recovery.status == "recommended"`.

- [x] **Step 3: Add executor adapter**

Adapter reads `run_id` from params and returns recovery plan output.

## Task 3: Verify and Report

**Files:**

- Modify: this plan checklist.
- Add: `docs/superpowers/notes/long-memory-agent/2026-05-20-phase48-recovery-tool-planner.md`

- [x] **Step 1: Run focused GREEN**

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_runs.py -q -k "plan_recovery_tools"
```

- [x] **Step 2: Run T1 module verification**

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py tests\test_writing_agent_planner.py tests\test_writing_agent_tool_registry.py -q
```

- [x] **Step 3: Static checks**

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

- [x] **Step 4: Write report, commit, push**
