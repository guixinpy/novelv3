# Phase147 Binding-Aware Continuation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface persisted write-step bindings in continuation and recovery summaries so the Agent can explain and recover from blocked writes by exact tool call and target resource.

**Architecture:** Reuse Phase146 persisted `WritingAgentStep.tool_call_id` and bounded `resource_binding`. Add those fields to continuation markers, failure summaries, and recovery preview source-step metadata without changing execution behavior.

**Tech Stack:** Python, pytest, existing Writing Agent run service and recovery planner.

---

## Scope

In scope:
- Include `tool_call_id` and `resource_binding` in continuation `blocked_tool`/`last_successful_tool`.
- Include the same binding summary in continuation `failure`.
- Include binding summary in recovery preview `source_step` and recovery hash payload when a recovery plan exists.

Out of scope:
- New recovery policies for resource binding mismatch.
- Frontend rendering.
- Tool execution changes.

## Files

- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/app/services/writing_agent/recovery_planner.py`
- Modify: `backend/tests/test_writing_agent_runs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase147-binding-aware-continuation.md`

## Task 1: Continuation State Binding Metadata

- [x] **Step 1: Add failing continuation assertions**

Update `backend/tests/test_writing_agent_runs.py::test_agent_run_execute_longform_chapter_batch_blocks_resource_binding_mismatch`:
- assert `payload["output"]["continuation_state"]["blocked_tool"]["tool_call_id"] == "toolcall:wrong"`
- assert blocked tool `resource_binding.target_id == "chapter:99"`
- assert `failure.tool_call_id == "toolcall:wrong"`
- assert `failure.resource_binding.target_id == "chapter:99"`

- [x] **Step 2: Run RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_execute_longform_chapter_batch_blocks_resource_binding_mismatch -q
```

Expected: fails because continuation markers do not include binding fields.

- [x] **Step 3: Implement continuation enrichment**

Modify `backend/app/services/writing_agent/run_service.py`:
- import or reuse `summarize_resource_binding`
- add `tool_call_id` and bounded `resource_binding` to `_step_marker()`
- add the same fields to `_failure_state()`

- [x] **Step 4: Run GREEN**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_execute_longform_chapter_batch_blocks_resource_binding_mismatch -q
```

Expected: test passes.

## Task 2: Recovery Preview Source Binding Metadata

- [x] **Step 1: Add failing recovery preview assertions**

Update an existing recovery preview test that has a recommended recovery to seed `tool_call_id` and `resource_binding` on the source `WritingAgentStep`, then assert:
- `output["source_step"]["tool_call_id"]` is present.
- `output["source_step"]["resource_binding"]["target_id"]` is present.
- `output["hash_payload"]["source_tool_call_id"]` is present.

- [x] **Step 2: Run RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_can_plan_recovery_tools_from_blocked_run -q
```

Expected: fails because recovery preview source-step metadata does not include bindings.

- [x] **Step 3: Implement recovery preview enrichment**

Modify `backend/app/services/writing_agent/recovery_planner.py`:
- import `summarize_resource_binding`
- include `source_tool_call_id` and bounded `source_resource_binding` in hash payload
- include `tool_call_id` and bounded `resource_binding` in `source_step`

- [x] **Step 4: Run GREEN**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_can_plan_recovery_tools_from_blocked_run -q
```

Expected: test passes.

## Task 3: Regression, Hygiene, Report, Commit

- [x] **Step 1: Run targeted regression**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_execute_longform_chapter_batch_blocks_resource_binding_mismatch backend\tests\test_writing_agent_runs.py::test_agent_run_can_plan_recovery_tools_from_blocked_run backend\tests\test_writing_agent_runs.py::test_agent_run_can_execute_approved_longform_chapter_batch_once backend\tests\test_writing_agent_trace_audit.py::test_inspect_agent_trace_audit_includes_dialog_approval_events_without_raw_hash -q
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

Create `docs/superpowers/notes/long-memory-agent/2026-05-23-phase147-binding-aware-continuation.md`.

- [x] **Step 4: Commit and push**

Run:

```powershell
git add backend/app/services/writing_agent/run_service.py backend/app/services/writing_agent/recovery_planner.py backend/tests/test_writing_agent_runs.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase147-binding-aware-continuation.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase147-binding-aware-continuation.md
git commit -m "feat: surface bindings in continuation state"
git push origin main
```

Expected: commit succeeds and push updates `origin/main`.
