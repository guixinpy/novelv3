# Phase144 Tool Call Resource Binding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add server-derived `tool_call_id` and `resource_binding` to write-step approval and audit surfaces.

**Architecture:** Introduce a small binding helper that derives stable call identity from trusted plan data, project id, step id, tool name, and mutation fingerprint target. Approval contracts, direct chapter prepare output, approval verification events, and trace audit summaries will expose the binding without adding database columns in this phase.

**Tech Stack:** Python, pytest, existing Writing Agent approval contract, mutation fingerprint, direct chapter generation approval path, trace audit.

---

## Scope

This phase implements contract-level and audit-level binding only.

In scope:
- Derive stable `tool_call_id` from server-side plan and write step data.
- Derive `resource_binding` for write steps from project id, plan id, step id, tool name, mutation fingerprint target, and source projection id.
- Expose binding in direct chapter prepare output.
- Include binding summaries in approval verification event and trace audit event chain.

Out of scope:
- Adding database columns to `writing_agent_steps`.
- Alembic migration.
- Hard execution-time comparison between expected and current binding.
- Full front-end rendering changes.

## Files

- Create: `backend/app/services/writing_agent/agent_step_binding.py`
- Create: `backend/tests/test_writing_agent_step_binding.py`
- Modify: `backend/app/services/writing_agent/approval_contract.py`
- Modify: `backend/app/services/writing_agent/chapter_generation_execution.py`
- Modify: `backend/app/services/writing_agent/approval_verification_event.py`
- Modify: `backend/app/services/writing_agent/agent_trace_audit.py`
- Modify: `backend/app/services/writing_agent/tool_registry.py`
- Modify: `backend/tests/test_writing_agent_approval_contract.py`
- Modify: `backend/tests/test_writing_agent_chapter_generation_execution.py`
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
- Modify: `backend/tests/test_writing_agent_trace_audit.py`
- Modify: `backend/tests/test_writing_agent_runs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase144-tool-call-resource-binding.md`

## Task 1: Binding Helper

- [x] **Step 1: Add failing binding helper tests**

Create `backend/tests/test_writing_agent_step_binding.py` with tests that assert:
- same inputs produce the same `tool_call_id`
- chapter mutation fingerprint produces `resource_binding.target_type == "chapter"` and `target_id == "chapter:2"`
- changing `step_id` changes `tool_call_id`

- [x] **Step 2: Run RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_step_binding.py -q
```

Expected: fails because `agent_step_binding` does not exist.

- [x] **Step 3: Implement helper**

Create `backend/app/services/writing_agent/agent_step_binding.py` with:
- `AGENT_STEP_BINDING_VERSION`
- `build_agent_step_binding(project_id, plan_id, source_projection_id, step, mutation_fingerprint)`
- `summarize_resource_binding(resource_binding)`
- stable SHA-256 based `tool_call_id`

- [x] **Step 4: Run GREEN**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_step_binding.py -q
```

Expected: tests pass.

## Task 2: Approval Contract Binding

- [x] **Step 1: Add failing approval contract expectations**

Update `backend/tests/test_writing_agent_approval_contract.py`:
- write step has `tool_call_id` starting with `toolcall:`
- write step has `resource_binding.binding_source == "server_derived"`
- verification drift includes `resource_binding_count == 1`
- `tool_call_ids == [step["tool_call_id"]]`

- [x] **Step 2: Run RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_approval_contract.py::test_approval_contract_attaches_mutation_fingerprint_to_write_steps backend\tests\test_writing_agent_approval_contract.py::test_verify_approval_contract_accepts_matching_hash -q
```

Expected: fails because contract lacks tool call binding fields.

- [x] **Step 3: Attach binding in approval contract**

Modify `backend/app/services/writing_agent/approval_contract.py`:
- pass `plan_id` and `source_projection_id` into `_approval_step`
- use `build_agent_step_binding()`
- add `tool_call_id` and `resource_binding` to write step
- add `tool_call_ids`, `resource_binding_count`, and `resource_bindings` to verification drift

- [x] **Step 4: Run GREEN**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_approval_contract.py -q
```

Expected: approval contract tests pass.

## Task 3: Direct Prepare and Tool Schema

- [x] **Step 1: Add failing direct prepare assertions**

Update `backend/tests/test_writing_agent_chapter_generation_execution.py`:
- direct plan step has `tool_call_id`
- top-level output includes same `tool_call_id`
- top-level output includes same `resource_binding`

Update `backend/tests/test_writing_agent_tool_registry.py` to assert prepare output schema contains `tool_call_id` and `resource_binding`.

- [x] **Step 2: Run RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_chapter_generation_execution.py::test_prepare_generate_chapter_execution_returns_agent_approval_contract backend\tests\test_writing_agent_tool_registry.py::test_agent_tool_registry_includes_approved_direct_chapter_generation_tools -q
```

Expected: fails until direct prepare and schema expose the binding fields.

- [x] **Step 3: Implement direct prepare surface**

Modify:
- `backend/app/services/writing_agent/chapter_generation_execution.py`
- `backend/app/services/writing_agent/tool_registry.py`

- [x] **Step 4: Run GREEN**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_chapter_generation_execution.py backend\tests\test_writing_agent_tool_registry.py::test_agent_tool_registry_includes_approved_direct_chapter_generation_tools -q
```

Expected: tests pass.

## Task 4: Verification Event and Trace Audit

- [x] **Step 1: Add failing event/audit assertions**

Update:
- `backend/tests/test_writing_agent_runs.py::test_agent_run_can_execute_approved_longform_chapter_batch_once`
- `backend/tests/test_writing_agent_trace_audit.py::test_inspect_agent_trace_audit_includes_dialog_approval_events_without_raw_hash`

Assertions:
- approval verification event includes `tool_call_ids`
- approval verification event includes bounded `resource_bindings`
- trace audit event chain preserves these fields without raw approval hashes

- [x] **Step 2: Run RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_can_execute_approved_longform_chapter_batch_once backend\tests\test_writing_agent_trace_audit.py::test_inspect_agent_trace_audit_includes_dialog_approval_events_without_raw_hash -q
```

Expected: fails because event builders do not include binding summaries.

- [x] **Step 3: Implement event and audit summaries**

Modify:
- `backend/app/services/writing_agent/approval_verification_event.py`
- `backend/app/services/writing_agent/agent_trace_audit.py`

- [x] **Step 4: Run GREEN**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_can_execute_approved_longform_chapter_batch_once backend\tests\test_writing_agent_trace_audit.py::test_inspect_agent_trace_audit_includes_dialog_approval_events_without_raw_hash -q
```

Expected: tests pass.

## Task 5: Regression, Hygiene, Report, Commit

- [x] **Step 1: Run targeted regression**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_step_binding.py backend\tests\test_writing_agent_approval_contract.py backend\tests\test_writing_agent_chapter_generation_execution.py backend\tests\test_writing_agent_tool_registry.py backend\tests\test_writing_agent_trace_audit.py backend\tests\test_writing_agent_runs.py::test_agent_run_can_execute_approved_longform_chapter_batch_once backend\tests\test_writing_agent_mutation_fingerprint.py -q
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

Create `docs/superpowers/notes/long-memory-agent/2026-05-23-phase144-tool-call-resource-binding.md`.

- [x] **Step 4: Commit and push**

Run:

```powershell
git add backend/app/services/writing_agent/agent_step_binding.py backend/app/services/writing_agent/approval_contract.py backend/app/services/writing_agent/chapter_generation_execution.py backend/app/services/writing_agent/approval_verification_event.py backend/app/services/writing_agent/agent_trace_audit.py backend/app/services/writing_agent/tool_registry.py backend/tests/test_writing_agent_step_binding.py backend/tests/test_writing_agent_approval_contract.py backend/tests/test_writing_agent_chapter_generation_execution.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_trace_audit.py backend/tests/test_writing_agent_runs.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase144-tool-call-resource-binding.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase144-tool-call-resource-binding.md
git commit -m "feat: bind write steps to tool calls"
git push origin main
```

Expected: commit succeeds and push updates `origin/main`.
