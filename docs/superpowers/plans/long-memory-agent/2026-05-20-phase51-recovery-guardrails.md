# Phase51 Recovery Guardrails Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add guardrails to recovery previews so unsafe or stale recovery plans cannot be executed even with a matching hash.

**Architecture:** Keep `recovery_policy.py` as the recovery recommendation source. Add guardrail checks inside `recovery_planner.py`, because preview should expose whether a plan is executable. `run_service.py` continues to trust `can_execute` and falls back to preview mode when guardrails block execution.

**Tech Stack:** FastAPI service layer, SQLAlchemy session, Writing Agent run/step records, deterministic recovery preview hashes, pytest API tests.

---

## Reference Assimilation

Phase51 adapts three reference patterns:

- `openclaw`: execution must bind to a durable planned context and reject stale/unsafe follow-up.
- `hermes-agent`: tool guardrails should produce structured rejection reasons instead of silently skipping or retrying.
- `openhuman`: state should be revalidated at execution time, and repeated failed work should not loop blindly.

The novelv3-specific translation is recovery guardrails for longform writing: a recovery tool can run only when it is visible in the current project tool plan, does not require missing user input, and has not already failed for the same source step and plan hash.

## Task 1: Write Failing Tests

**Files:**

- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Add requires-user-input guardrail test**

Add `test_agent_recovery_preview_blocks_requires_user_input`.

Create a bare project and run `preflight_writing` for chapter 1. Missing setup should recommend `generate_setup` and require `command_args`.

Expected assertions:

```python
preview = response.json()["steps"][0]["output"]
assert preview["recovery"]["reason_code"] == "missing_setup"
assert preview["can_execute"] is False
assert preview["guardrails"]["status"] == "blocked"
assert preview["guardrails"]["blockers"][0]["code"] == "requires_user_input"
assert preview["execution_policy"]["status"] == "requires_user_input"
```

- [x] **Step 2: Add hidden-tool guardrail test**

Add `test_agent_recovery_execute_rejects_hidden_tool_after_state_drift`.

Create a missing-outline recovery plan, capture `plan_hash`, then delete the project's `Storyline` before confirmed execute. `expand_outline_window` should become hidden because its availability checks require a storyline.

Expected assertions:

```python
assert payload["input"]["planner"]["mode"] == "preview"
assert payload["input"]["planner"]["execution_policy"]["status"] == "tool_not_visible"
assert [step["tool_name"] for step in payload["steps"]] == ["plan_recovery_tools"]
preview = payload["steps"][0]["output"]
assert preview["can_execute"] is False
assert preview["guardrails"]["blockers"][0]["code"] == "tool_not_visible"
```

- [x] **Step 3: Add repeated-failed-plan guardrail test**

Add `test_agent_recovery_preview_blocks_repeated_failed_plan`.

Create a missing-outline recovery plan, then insert a failed recovery execution run with the same `plan_hash` in its `input.planner`.

Expected assertions:

```python
preview = response.json()["steps"][0]["output"]
assert preview["can_execute"] is False
assert preview["guardrails"]["status"] == "blocked"
assert preview["guardrails"]["blockers"][0]["code"] == "repeat_failed_recovery"
assert preview["execution_policy"]["status"] == "repeat_failed_recovery"
```

- [x] **Step 4: Verify RED**

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "recovery_preview_blocks_requires_user_input or hidden_tool_after_state_drift or repeated_failed_plan"
```

Expected: FAIL because recovery preview does not yet expose guardrails.

## Task 2: Implement Guardrails

**Files:**

- Modify: `backend/app/services/writing_agent/recovery_planner.py`
- Modify: `backend/app/services/writing_agent/run_service.py`

- [x] **Step 1: Import tool registry projection**

In `recovery_planner.py`, import:

```python
from app.services.writing_agent.tool_registry import allowed_tool_names, build_agent_tool_plan
```

- [x] **Step 2: Add guardrail helper**

Add `_recovery_guardrails(db, project_id, tool, recovery, plan_hash)` returning:

```python
{
    "status": "ready" | "blocked",
    "checks": [...],
    "blockers": [...],
}
```

Guardrail checks:

- `requires_user_input` when `recovery.requires_user_input is True`;
- `tool_not_allowed` when the recovery tool is missing from registry;
- `tool_not_visible` when the current `build_agent_tool_plan()` hides the tool;
- `repeat_failed_recovery` when a previous failed recovery execution run has the same `plan_hash`.

- [x] **Step 3: Wire guardrails into preview output**

Set:

```python
guardrails = _recovery_guardrails(...)
can_execute = tool is not None and guardrails["status"] == "ready"
execution_policy["status"] = "ready" if can_execute else guardrails["blockers"][0]["code"]
```

Include `guardrails` in preview output.

- [x] **Step 4: Preserve exact guardrail status in auto-plan fallback**

In `run_service.py`, when `plan.get("can_execute") is not True`, pass:

```python
status = str(((plan.get("execution_policy") or {}).get("status")) or "not_executable")
```

to `_recovery_preview_auto_plan()`.

## Task 3: Verify and Report

**Files:**

- Modify: this plan checklist.
- Add: `docs/superpowers/notes/long-memory-agent/2026-05-20-phase51-recovery-guardrails.md`

- [x] **Step 1: Run focused GREEN**

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "recovery_preview_blocks_requires_user_input or hidden_tool_after_state_drift or repeated_failed_plan"
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
