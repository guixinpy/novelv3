# Phase145 Execution Binding Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Block approved mutating tool execution when the approved resource binding does not match the resource about to be written.

**Architecture:** Reuse Phase144 `resource_binding` summaries as the execution guard input. Add a small verifier in `agent_step_binding.py`, then apply it before direct chapter generation and longform batch chapter execution dispatch `generate_chapter`.

**Tech Stack:** Python, pytest, existing Writing Agent approval contracts, direct chapter generation execution, longform batch execution.

---

## Scope

In scope:
- Verify approved `generate_chapter` binding target before executing chapter writes.
- Block execution if binding is missing or points to another chapter.
- Surface `execution_resource_binding` in success and blocked outputs.
- Keep this phase service-side only.

Out of scope:
- Database columns or Alembic migration.
- Frontend display of binding guard details.
- General multi-tool binding policy beyond `generate_chapter`.

## Files

- Modify: `backend/app/services/writing_agent/agent_step_binding.py`
- Modify: `backend/app/services/writing_agent/chapter_generation_execution.py`
- Modify: `backend/app/services/writing_agent/batch_execution.py`
- Modify: `backend/tests/test_writing_agent_step_binding.py`
- Modify: `backend/tests/test_writing_agent_chapter_generation_execution.py`
- Modify: `backend/tests/test_writing_agent_runs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase145-execution-binding-guard.md`

## Task 1: Binding Guard Helper

- [x] **Step 1: Add failing helper tests**

Update `backend/tests/test_writing_agent_step_binding.py` with tests for:
- `verify_resource_binding_target()` returns ready when the approved binding matches `generate_chapter -> chapter:2`.
- It returns blocked with `reason == "resource_binding_target_mismatch"` when the only approved binding points at `chapter:3`.
- It returns blocked with `reason == "resource_binding_missing"` when no approved binding exists for the tool.

- [x] **Step 2: Run RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_step_binding.py -q
```

Expected: fails because `verify_resource_binding_target` is not implemented.

- [x] **Step 3: Implement helper**

Modify `backend/app/services/writing_agent/agent_step_binding.py`:
- Add `verify_resource_binding_target(verification, tool_name, target_type, target_id)`.
- Read bindings from `verification["drift"]["resource_bindings"]`.
- Return a compact dict with `status`, `reason`, `expected`, `resource_binding`, and `resource_bindings`.

- [x] **Step 4: Run GREEN**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_step_binding.py -q
```

Expected: all helper tests pass.

## Task 2: Direct Chapter Execution Guard

- [x] **Step 1: Add failing direct execution tests**

Update `backend/tests/test_writing_agent_chapter_generation_execution.py`:
- Existing approved direct execution success should include `execution_resource_binding.status == "ready"`.
- New mismatch test monkeypatches `verify_agent_plan_approval_contract` to return a ready verification with `resource_bindings[0].target_id == "chapter:99"`, then asserts:
  - output status is `blocked`
  - reason is `resource_binding_target_mismatch`
  - fake generation is not called
  - `execution_resource_binding.status == "blocked"`

- [x] **Step 2: Run RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_chapter_generation_execution.py::test_execute_generate_chapter_with_approval_runs_after_contract_verification backend\tests\test_writing_agent_chapter_generation_execution.py::test_execute_generate_chapter_with_approval_blocks_resource_binding_mismatch -q
```

Expected: fails because direct execution does not yet expose or enforce `execution_resource_binding`.

- [x] **Step 3: Implement direct guard**

Modify `backend/app/services/writing_agent/chapter_generation_execution.py`:
- Import `verify_resource_binding_target`.
- After approval verification is ready, verify `generate_chapter` target `chapter:{chapter_index}`.
- On blocked guard, return `_blocked_output(..., reason=binding_check["reason"], extra={...})`.
- On success, add `execution_resource_binding` to generation output.

- [x] **Step 4: Run GREEN**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_chapter_generation_execution.py -q
```

Expected: direct chapter execution tests pass.

## Task 3: Longform Batch Execution Guard

- [x] **Step 1: Add failing batch execution tests**

Update `backend/tests/test_writing_agent_runs.py`:
- Existing approved batch execution success should include `output["execution_resource_binding"]["status"] == "ready"`.
- Add a batch mismatch test that monkeypatches `app.services.writing_agent.batch_execution.verify_agent_plan_approval_contract` to return ready verification with `resource_bindings[0].target_id == "chapter:99"`, then asserts:
  - response status is 200
  - run status is `blocked`
  - output reason is `resource_binding_target_mismatch`
  - no chapter 2 content is created

- [x] **Step 2: Run RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_can_execute_approved_longform_chapter_batch_once backend\tests\test_writing_agent_runs.py::test_agent_run_execute_longform_chapter_batch_blocks_resource_binding_mismatch -q
```

Expected: fails because batch execution does not yet enforce binding target.

- [x] **Step 3: Implement batch guard**

Modify `backend/app/services/writing_agent/batch_execution.py`:
- Import `verify_resource_binding_target`.
- After approval verification is ready and before `ActionExecutionService.execute()`, verify `generate_chapter` target `chapter:{chapter_index}`.
- Return blocked output with `execution_resource_binding`, `agent_plan_approval_verification`, and `approval_verification_event` when the guard blocks.
- Add `execution_resource_binding` to successful output.
- Add binding mismatch reasons to `_recommended_next_tools()` as `["prepare_longform_chapter_batch_execution"]`.

- [x] **Step 4: Run GREEN**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_can_execute_approved_longform_chapter_batch_once backend\tests\test_writing_agent_runs.py::test_agent_run_execute_longform_chapter_batch_blocks_resource_binding_mismatch -q
```

Expected: batch execution guard tests pass.

## Task 4: Tool Registry Schema Sync

- [x] **Step 1: Add failing schema assertions**

Update `backend/tests/test_writing_agent_tool_registry.py`:
- `execute_generate_chapter_with_approval` output schema includes `execution_resource_binding`.
- `execute_longform_chapter_batch` output schema includes `agent_plan_approval_verification` and `execution_resource_binding`.

- [x] **Step 2: Run RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_tool_registry.py::test_agent_tool_registry_includes_approved_direct_chapter_generation_tools backend\tests\test_writing_agent_tool_registry.py::test_agent_tool_registry_includes_execute_longform_chapter_batch -q
```

Expected: fails because schemas do not expose execution binding.

- [x] **Step 3: Implement schema update**

Modify `backend/app/services/writing_agent/tool_registry.py`.

- [x] **Step 4: Run GREEN**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_tool_registry.py::test_agent_tool_registry_includes_approved_direct_chapter_generation_tools backend\tests\test_writing_agent_tool_registry.py::test_agent_tool_registry_includes_execute_longform_chapter_batch -q
```

Expected: schema tests pass.

## Task 5: Regression, Hygiene, Report, Commit

- [x] **Step 1: Run targeted regression**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_step_binding.py backend\tests\test_writing_agent_chapter_generation_execution.py backend\tests\test_writing_agent_runs.py::test_agent_run_can_execute_approved_longform_chapter_batch_once backend\tests\test_writing_agent_runs.py::test_agent_run_execute_longform_chapter_batch_blocks_resource_binding_mismatch backend\tests\test_writing_agent_approval_contract.py backend\tests\test_writing_agent_trace_audit.py backend\tests\test_writing_agent_tool_registry.py::test_agent_tool_registry_includes_approved_direct_chapter_generation_tools backend\tests\test_writing_agent_tool_registry.py::test_agent_tool_registry_includes_execute_longform_chapter_batch -q
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

Create `docs/superpowers/notes/long-memory-agent/2026-05-23-phase145-execution-binding-guard.md`.

- [x] **Step 4: Commit and push**

Run:

```powershell
git add backend/app/services/writing_agent/agent_step_binding.py backend/app/services/writing_agent/chapter_generation_execution.py backend/app/services/writing_agent/batch_execution.py backend/app/services/writing_agent/tool_registry.py backend/tests/test_writing_agent_step_binding.py backend/tests/test_writing_agent_chapter_generation_execution.py backend/tests/test_writing_agent_runs.py backend/tests/test_writing_agent_tool_registry.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase145-execution-binding-guard.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase145-execution-binding-guard.md
git commit -m "feat: guard writes with resource bindings"
git push origin main
```

Expected: commit succeeds and push updates `origin/main`.
