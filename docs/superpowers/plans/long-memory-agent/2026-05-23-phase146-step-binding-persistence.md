# Phase146 Step Binding Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist `tool_call_id` and bounded `resource_binding` on `WritingAgentStep` records so trace audit and run detail can inspect write bindings without depending only on nested tool output.

**Architecture:** Add nullable columns to `writing_agent_steps`, hydrate them from tool outputs in `WritingAgentRunService`, and expose them through Pydantic output schemas plus trace audit summaries. Existing historical steps remain valid because the new fields are nullable.

**Tech Stack:** Python, SQLAlchemy, Alembic, pytest, existing Writing Agent run service and trace audit.

---

## Scope

In scope:
- Add `tool_call_id` and `resource_binding` to the `WritingAgentStep` model.
- Add Alembic migration for the new nullable columns.
- Persist bindings from `execution_resource_binding.resource_binding`, direct `resource_binding`, or approval verification event summaries.
- Expose persisted fields in `WritingAgentStepOut`, trace audit step summaries, and event chain tool-step events.

Out of scope:
- Backfilling historical rows.
- New frontend display.
- Exact `tool_call_id` step-level execution policy for multi-write plans.

## Files

- Create: `backend/alembic/versions/20260523_add_writing_agent_step_bindings.py`
- Modify: `backend/app/models/writing_agent.py`
- Modify: `backend/app/schemas/writing_agent.py`
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/app/services/writing_agent/agent_trace_audit.py`
- Modify: `backend/tests/test_writing_agent_runs.py`
- Modify: `backend/tests/test_writing_agent_trace_audit.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase146-step-binding-persistence.md`

## Task 1: Model and Schema Fields

- [x] **Step 1: Add failing model/schema assertions**

Update `backend/tests/test_writing_agent_trace_audit.py` or a narrow existing Writing Agent test to assert:
- `hasattr(WritingAgentStep, "tool_call_id")`
- `hasattr(WritingAgentStep, "resource_binding")`
- `WritingAgentStepOut.model_fields` includes both fields.

- [x] **Step 2: Run RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_trace_audit.py::test_writing_agent_step_binding_fields_are_modelled -q
```

Expected: fails because the fields are not modelled yet.

- [x] **Step 3: Implement model/schema fields**

Modify:
- `backend/app/models/writing_agent.py`
- `backend/app/schemas/writing_agent.py`

Add:
- `tool_call_id = Column(String, nullable=True)`
- `resource_binding = Column(JSON, nullable=True)`
- matching nullable fields on `WritingAgentStepOut`.

- [x] **Step 4: Run GREEN**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_trace_audit.py::test_writing_agent_step_binding_fields_are_modelled -q
```

Expected: test passes.

## Task 2: Persist Bindings on Step Completion

- [x] **Step 1: Add failing run-service assertions**

Update `backend/tests/test_writing_agent_runs.py::test_agent_run_can_execute_approved_longform_chapter_batch_once`:
- query the persisted `WritingAgentStep`
- assert `step.tool_call_id` starts with `toolcall:`
- assert `step.resource_binding["target_id"] == "chapter:2"`
- assert the API payload step includes matching fields.

- [x] **Step 2: Run RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_can_execute_approved_longform_chapter_batch_once -q
```

Expected: fails because step completion does not persist or serialize binding fields.

- [x] **Step 3: Implement persistence helper**

Modify `backend/app/services/writing_agent/run_service.py`:
- Add `_extract_step_resource_binding(output)`.
- In `_complete_step()`, set `step.resource_binding` and `step.tool_call_id`.
- In `_block_step_and_run()`, set the same fields from blocked output.
- Prefer `output["execution_resource_binding"]["resource_binding"]`, then `output["resource_binding"]`, then first `output["approval_verification_event"]["resource_bindings"]`.

- [x] **Step 4: Run GREEN**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_can_execute_approved_longform_chapter_batch_once -q
```

Expected: test passes.

## Task 3: Trace Audit Step Summary

- [x] **Step 1: Add failing trace audit assertions**

Update `backend/tests/test_writing_agent_trace_audit.py::test_inspect_agent_trace_audit_includes_dialog_approval_events_without_raw_hash`:
- seed `WritingAgentStep(tool_call_id="toolcall:test", resource_binding={...})`
- assert `output["steps"][0]["tool_call_id"] == "toolcall:test"`
- assert `output["steps"][0]["resource_binding"]["target_id"] == "chapter:2"`
- assert `output["event_chain"][2]["tool_call_id"] == "toolcall:test"`

- [x] **Step 2: Run RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_trace_audit.py::test_inspect_agent_trace_audit_includes_dialog_approval_events_without_raw_hash -q
```

Expected: fails because trace audit summaries do not include persisted binding fields.

- [x] **Step 3: Implement trace audit exposure**

Modify `backend/app/services/writing_agent/agent_trace_audit.py`:
- Include `tool_call_id` and bounded `resource_binding` in `_step_summary()`.
- Include the same fields in `tool_step` event chain entries.

- [x] **Step 4: Run GREEN**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_trace_audit.py::test_inspect_agent_trace_audit_includes_dialog_approval_events_without_raw_hash -q
```

Expected: test passes.

## Task 4: Alembic Migration

- [x] **Step 1: Create migration**

Create `backend/alembic/versions/20260523_add_writing_agent_step_bindings.py`:
- `down_revision = "20260518_add_writing_agent_runs"`
- Add nullable `tool_call_id` string column.
- Add nullable `resource_binding` JSON column.
- Add index `ix_writing_agent_steps_project_tool_call` on `project_id`, `tool_call_id`.

- [x] **Step 2: Run migration smoke tests**

Run:

```powershell
backend\.venv\Scripts\python.exe -m py_compile backend\alembic\versions\20260523_add_writing_agent_step_bindings.py
```

Expected: compile succeeds.

Run:

```powershell
Push-Location backend
$env:MOZHOU_DATABASE_URL = "sqlite:///../.tmp/phase146_alembic.db"
.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
Pop-Location
```

Expected: migration chain applies through `20260523_add_writing_agent_step_bindings`.

## Task 5: Regression, Hygiene, Report, Commit

- [x] **Step 1: Run targeted regression**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_can_execute_approved_longform_chapter_batch_once backend\tests\test_writing_agent_runs.py::test_agent_run_execute_longform_chapter_batch_blocks_resource_binding_mismatch backend\tests\test_writing_agent_trace_audit.py::test_writing_agent_step_binding_fields_are_modelled backend\tests\test_writing_agent_trace_audit.py::test_inspect_agent_trace_audit_includes_dialog_approval_events_without_raw_hash backend\tests\test_writing_agent_chapter_generation_execution.py backend\tests\test_writing_agent_step_binding.py -q
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

Create `docs/superpowers/notes/long-memory-agent/2026-05-23-phase146-step-binding-persistence.md`.

- [x] **Step 4: Commit and push**

Run:

```powershell
git add backend/alembic/versions/20260523_add_writing_agent_step_bindings.py backend/app/models/writing_agent.py backend/app/schemas/writing_agent.py backend/app/services/writing_agent/run_service.py backend/app/services/writing_agent/agent_trace_audit.py backend/tests/test_writing_agent_runs.py backend/tests/test_writing_agent_trace_audit.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase146-step-binding-persistence.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase146-step-binding-persistence.md
git commit -m "feat: persist writing agent step bindings"
git push origin main
```

Expected: commit succeeds and push updates `origin/main`.
