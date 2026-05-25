# Phase151 Planner Recovery Intent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the Writing Agent planner route "recover/continue blocked run" user intent to `plan_recovery_tools` without requiring the user to manually specify that tool.

**Architecture:** Add a narrow planner intent class, `recover_blocked_run`, that selects the latest blocked/failed run with a recommended recovery and plans a preview-only `plan_recovery_tools` step. This keeps recovery execution behind the existing `recovery_run_id + recovery_plan_hash + confirm_execute` gates and does not change write execution behavior.

**Tech Stack:** Python, SQLAlchemy, pytest, existing Writing Agent planner and run service.

---

## Scope

In scope:
- Add planner support for recovery intent words such as "恢复上一轮阻塞" and "继续上一轮失败".
- Find the latest project-scoped blocked/failed run that contains `agent_tool_result.recovery.status == "recommended"`.
- Generate a read-only `plan_recovery_tools` plan for that run.
- Ensure API `auto_plan` uses this planner path when the user only provides a recovery goal.

Out of scope:
- Executing recovery automatically.
- Changing `execute_recovery` confirmation gates.
- Changing frontend UI.
- Adding broad natural-language recovery inference beyond explicit blocked/failed/recovery wording.

## Files

- Modify: `backend/app/services/writing_agent/planner.py`
- Modify: `backend/tests/test_writing_agent_planner.py`
- Modify: `backend/tests/test_writing_agent_runs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase151-planner-recovery-intent.md`

## Task 1: Planner Recovery Intent

- [x] **Step 1: Write failing planner test**

Add `test_planner_routes_recovery_intent_to_latest_recoverable_run` in `backend/tests/test_writing_agent_planner.py`:
- seed a project.
- create a blocked `WritingAgentRun`.
- create a blocked `WritingAgentStep` whose output envelope contains:
  - `agent_tool_result.recovery.status == "recommended"`
  - `next_tool == "prepare_generate_chapter_execution"`
- call `build_writing_agent_run_plan(..., goal="恢复上一轮阻塞")`.
- assert:
  - `intent_class == "recover_blocked_run"`
  - tools are `["describe_agent_tools", "plan_recovery_tools"]`
  - `plan_recovery_tools.params == {"run_id": blocked_run.id}`
  - approval contract is `not_required`.

- [x] **Step 2: Run RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_planner.py::test_planner_routes_recovery_intent_to_latest_recoverable_run -q
```

Expected: fails because the planner does not classify or build recovery intent yet.

- [x] **Step 3: Implement planner recovery intent**

Modify `backend/app/services/writing_agent/planner.py`:
- import `WritingAgentRun` and `WritingAgentStep`.
- add `RECOVER_BLOCKED_RUN_INTENT = "recover_blocked_run"` or inline string.
- update `_classify_intent()` to return `recover_blocked_run` when explicit intent matches or when the goal includes recovery wording.
- add `_build_recover_blocked_run_plan(...)`.
- add `_latest_recoverable_run_id(...)`.
- selected recovery step:
  - `tool_name="plan_recovery_tools"`
  - `params={"run_id": run_id}`
  - `reason="预览上一轮阻塞或失败运行的恢复工具链，不直接执行恢复。"`
  - `on_missing="stop"`
  - `on_failure="stop"`
  - `expected_output="恢复工具链预览。"`
- if no run exists, set risk flag `missing_recoverable_run` and rejected tool reason.

- [x] **Step 4: Run GREEN**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_planner.py::test_planner_routes_recovery_intent_to_latest_recoverable_run -q
```

Expected: passes.

## Task 2: API Auto-Plan Recovery Intent

- [x] **Step 1: Write failing API test**

Add `test_agent_run_auto_plan_recovers_latest_blocked_run_from_goal` in `backend/tests/test_writing_agent_runs.py`:
- create a project and a blocked source run with recommended recovery.
- call `/agent-runs` with:
  - goal: `"恢复上一轮阻塞"`
  - input: `{"auto_plan": True}`
- assert:
  - planner intent is `recover_blocked_run`
  - input tools contain `plan_recovery_tools`
  - executed steps are `["describe_agent_tools", "plan_recovery_tools"]`
  - `plan_recovery_tools.params.run_id` equals the blocked run id.

- [x] **Step 2: Run RED/GREEN as appropriate**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_auto_plan_recovers_latest_blocked_run_from_goal -q
```

Expected: after Task 1 implementation this should pass; if it fails, make the smallest integration fix.

## Task 3: Regression, Hygiene, Report, Commit

- [x] **Step 1: Run targeted regression**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_planner.py::test_planner_routes_recovery_intent_to_latest_recoverable_run backend\tests\test_writing_agent_planner.py::test_planner_builds_ready_next_chapter_tool_chain backend\tests\test_writing_agent_runs.py::test_agent_run_auto_plan_recovers_latest_blocked_run_from_goal backend\tests\test_writing_agent_runs.py::test_agent_run_auto_plan_previews_recovery_tool_plan_by_default -q
```

- [x] **Step 2: Run hygiene checks**

Run:

```powershell
git diff --check
```

Run:

```powershell
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

- [x] **Step 3: Write phase report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-23-phase151-planner-recovery-intent.md`.

- [x] **Step 4: Commit and push**

Commit message:

```text
feat: route recovery intent to blocked run preview
```
