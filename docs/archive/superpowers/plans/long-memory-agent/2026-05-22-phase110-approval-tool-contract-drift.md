# Phase110 Approval Tool Contract Drift Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the read-only approval verifier so each write step reports current tool-contract drift before a future execution gate trusts an approval hash.

**Architecture:** `approval_contract.py` remains a pure approval/verification module and accepts optional tool metadata supplied by the executor. `tool_executor.py` builds current metadata from the tool registry, static adapters, and `agent_tool_execution_metadata()` to avoid circular imports and keep the check read-only.

**Tech Stack:** Python, pytest, Writing Agent service layer, existing T0/T1 validation flow.

---

## Phase Context

Phase109 verifies approval contract hash, approved snapshot, and project binding. Phase110 adds a second read-only guard: after hash/project checks pass, verify that write steps still point to Agent-callable tools whose current contract has not drifted into an unsafe or unusable state.

This serves the long-memory Writing Agent goal by making plan approval a tool-contract-aware control-plane step, without executing writes.

## Assumptions

- Approval preview and verification must remain read-only.
- `approval_contract.py` should not import `tool_executor.py`; doing so risks circular dependency and mixes pure contract logic with runtime adapter lookup.
- `tool_executor.py` can safely inject live metadata because it already owns static adapter visibility and can read registry descriptors.
- Required-field validation only checks JSON schema `required`; tools that do not declare `required` fields are not blocked by missing optional params.

## Not Doing

- Do not execute any write tool.
- Do not change write-tool confirmation semantics.
- Do not redesign all tool schemas.
- Do not generate novel chapters in this phase.
- Do not run full frontend/backend verification unless local T1 signals show broader risk.

## Task 1: Add Failing Approval Contract Unit Tests

**Files:**
- Modify: `backend/tests/test_writing_agent_approval_contract.py`

- [ ] Add tests that call `verify_agent_plan_approval_contract(..., tool_metadata_by_name=...)`.
- [ ] Cover ready metadata, missing required step params, and drifted read-only/no-confirmation tool state.
- [ ] Run focused pytest and confirm RED because `tool_metadata_by_name` and drift output do not exist yet.

Command:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_approval_contract.py -q
```

Expected RED:

```text
TypeError: verify_agent_plan_approval_contract() got an unexpected keyword argument 'tool_metadata_by_name'
```

## Task 2: Add Executor Metadata Injection Test

**Files:**
- Modify: `backend/tests/test_writing_agent_tool_executor.py`

- [ ] Extend the existing approval verification executor test.
- [ ] Assert `drift.tool_contracts_checked is True`.
- [ ] Assert the write step reports `generate_chapter`, `tool_exists`, `adapter_exists`, write mutability, confirmation required, and `status == "ready"`.
- [ ] Run focused pytest and confirm RED because executor does not inject metadata yet.

Command:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py -k "approval_contract_verification" -q
```

Expected RED:

```text
KeyError: 'tool_contracts_checked'
```

## Task 3: Implement Pure Drift Checking

**Files:**
- Modify: `backend/app/services/writing_agent/approval_contract.py`

- [ ] Add optional `tool_metadata_by_name` to `verify_agent_plan_approval_contract()`.
- [ ] Add drift fields:
  - `tool_contracts_checked`
  - `tool_contract_drift_count`
  - `tool_contracts`
- [ ] For each write step, report:
  - `step_id`
  - `tool_name`
  - `tool_exists`
  - `adapter_exists`
  - `current_mutability`
  - `current_requires_confirmation`
  - `required_fields`
  - `missing_required_fields`
  - `status`
  - `reasons`
- [ ] Block with `reason == "tool_contract_drift"` after hash/snapshot/project checks pass when any write-step contract is not ready.
- [ ] Recommend `inspect_agent_tool_contracts` for tool drift.

## Task 4: Inject Runtime Tool Metadata From Executor

**Files:**
- Modify: `backend/app/services/writing_agent/tool_executor.py`

- [ ] Import or locally use `agent_tool_execution_metadata()`.
- [ ] Add a helper that builds metadata only for write/guarded-write or confirmation-required plan steps.
- [ ] Use `get_agent_tool_descriptor()`, `_STATIC_TOOL_ADAPTERS`, `adapter.to_metadata()`, and descriptor `input_schema.required`.
- [ ] Pass `tool_metadata_by_name` into `verify_agent_plan_approval_contract()`.

## Task 5: Verification and Report

**Files:**
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-22-phase110-approval-tool-contract-drift.md`

- [ ] Run focused approval contract tests.
- [ ] Run related executor tests.
- [ ] Run T1 module suite for approval/tool registry/executor.
- [ ] Run `git diff --check`.
- [ ] Run active secret scan over changed backend/docs paths.
- [ ] Write Phase110 report with actual commands and outputs.

T1 target:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_approval_contract.py backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py -q
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```
