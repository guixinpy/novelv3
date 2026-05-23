# Phase148 Binding Recovery Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route `resource_binding_missing` and `resource_binding_target_mismatch` blocked writes to a safe re-prepare recovery plan.

**Architecture:** Extend the existing Writing Agent recovery policy, not the execution guard. Binding recovery recommends only prepare/read tools (`prepare_longform_chapter_batch_execution` or `prepare_generate_chapter_execution`) so a fresh approval contract is required before any write can resume.

**Tech Stack:** Python, pytest, existing Writing Agent recovery policy, run service continuation state, recovery preview planner.

---

## Scope

In scope:
- Add recovery policy for blocked `execute_longform_chapter_batch` binding failures.
- Add recovery policy for blocked `execute_generate_chapter_with_approval` binding failures.
- Expose the recovery in continuation state and `plan_recovery_tools` preview.

Out of scope:
- Auto-executing recovered write tools.
- Changing resource binding verification logic.
- Frontend rendering.

## Files

- Modify: `backend/app/services/writing_agent/recovery_policy.py`
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`
- Modify: `backend/tests/test_writing_agent_chapter_generation_execution.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase148-binding-recovery-policy.md`

## Task 1: Longform Batch Binding Recovery

- [x] **Step 1: Add failing batch recovery assertions**

Update `backend/tests/test_writing_agent_runs.py::test_agent_run_execute_longform_chapter_batch_blocks_resource_binding_mismatch`:
- assert `continuation["recovery"]["status"] == "recommended"`
- assert `continuation["recovery"]["reason_code"] == "resource_binding_target_mismatch"`
- assert `continuation["recovery"]["next_tool"] == "prepare_longform_chapter_batch_execution"`
- assert `continuation["recovery"]["next_params"] == {"task_id": prepared["task_id"]}`
- call `plan_recovery_tools` for the blocked run and assert it returns the same prepare tool and params.

- [x] **Step 2: Run RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_execute_longform_chapter_batch_blocks_resource_binding_mismatch -q
```

Expected: fails because resource binding mismatch currently has no recommended recovery.

- [x] **Step 3: Implement batch recovery policy**

Modify `backend/app/services/writing_agent/recovery_policy.py`:
- Add `_binding_recovery(tool_name, output, planner)`.
- For `execute_longform_chapter_batch`, extract `task.id` from output and return:
  - `next_tool: "prepare_longform_chapter_batch_execution"`
  - `next_params: {"task_id": task_id}`
  - `requires_user_input: False`
  - `affected_chapter_indexes` from `output["chapter_index"]` if available.

- [x] **Step 4: Run GREEN**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_execute_longform_chapter_batch_blocks_resource_binding_mismatch -q
```

Expected: batch mismatch recovery assertions pass.

## Task 2: Direct Chapter Binding Recovery

- [x] **Step 1: Add failing direct recovery assertions**

Update `backend/tests/test_writing_agent_chapter_generation_execution.py::test_execute_generate_chapter_with_approval_blocks_resource_binding_mismatch`:
- import `build_writing_agent_recovery`
- call it with `tool_name="execute_generate_chapter_with_approval"`, `step_status="blocked"`, and the blocked output.
- assert:
  - `status == "recommended"`
  - `reason_code == "resource_binding_target_mismatch"`
  - `next_tool == "prepare_generate_chapter_execution"`
  - `next_params == {"chapter_index": 2}`
  - `requires_user_input is False`

- [x] **Step 2: Run RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_chapter_generation_execution.py::test_execute_generate_chapter_with_approval_blocks_resource_binding_mismatch -q
```

Expected: fails because direct binding mismatch has no recovery policy.

- [x] **Step 3: Implement direct recovery policy**

Modify `_binding_recovery()`:
- For `execute_generate_chapter_with_approval`, extract `chapter_index` from output and return:
  - `next_tool: "prepare_generate_chapter_execution"`
  - `next_params: {"chapter_index": chapter_index}`
  - `requires_user_input: False`

- [x] **Step 4: Run GREEN**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_chapter_generation_execution.py::test_execute_generate_chapter_with_approval_blocks_resource_binding_mismatch -q
```

Expected: direct recovery assertions pass.

## Task 3: Regression, Hygiene, Report, Commit

- [x] **Step 1: Run targeted regression**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_execute_longform_chapter_batch_blocks_resource_binding_mismatch backend\tests\test_writing_agent_chapter_generation_execution.py::test_execute_generate_chapter_with_approval_blocks_resource_binding_mismatch backend\tests\test_writing_agent_runs.py::test_agent_run_can_plan_recovery_tools_from_blocked_run backend\tests\test_writing_agent_runs.py::test_agent_run_can_execute_approved_longform_chapter_batch_once -q
```

Expected: all selected tests pass.

- [x] **Step 2: Run hygiene checks**

Run:

```powershell
git diff --check
```

Run:

```powershell
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

Expected: no whitespace errors and no committed API key leaks.

- [x] **Step 3: Write phase report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-23-phase148-binding-recovery-policy.md`.

- [ ] **Step 4: Commit and push**

Run:

```powershell
git add backend/app/services/writing_agent/recovery_policy.py backend/tests/test_writing_agent_runs.py backend/tests/test_writing_agent_chapter_generation_execution.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase148-binding-recovery-policy.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase148-binding-recovery-policy.md
git commit -m "feat: recover binding drift with fresh approval"
git push origin main
```

Expected: commit succeeds and push updates `origin/main`.
