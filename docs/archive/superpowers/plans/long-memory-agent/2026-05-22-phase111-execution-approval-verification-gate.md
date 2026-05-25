# Phase111 Execution Approval Verification Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Require fresh Writing Agent plan approval verification evidence before `execute_longform_chapter_batch` reaches chapter generation.

**Architecture:** Batch prepare persists a narrow Agent plan and its approval contract for the selected `generate_chapter` write step. Batch execution keeps its existing Phase61 approval hash gate, then runs a fresh Phase109/110 verifier against the persisted Agent plan using runtime tool metadata injected by `tool_executor.py`.

**Tech Stack:** Python, pytest, SQLAlchemy service layer, Writing Agent tool executor.

---

## Phase Context

Phase110 made approval verification aware of live tool-contract drift. Phase111 connects that read-only verification to a real controlled execution path, without expanding verifier scope or forcing all write tools through a new generic executor yet.

Target path:

```text
prepare_longform_chapter_batch_execution
  -> persist attempt_manifest
  -> persist Phase61 approval_contract
  -> persist Agent plan for generate_chapter
  -> persist Agent plan approval contract

execute_longform_chapter_batch
  -> validate existing Phase61 approval_contract_hash
  -> fresh verify persisted Agent plan approval contract
  -> execute generate_chapter only if verification is ready
```

## Assumptions

- Phase111 should target the existing longform batch execution path because it already has a controlled `confirm_execute + approval_contract_hash` gate.
- The persisted Agent plan should model the selected write step that actually mutates novel content: `generate_chapter`.
- `execute_longform_chapter_batch` should receive runtime tool metadata from its caller, rather than importing `tool_executor.py`.
- This phase should not make direct one-off `generate_chapter` calls require approval yet; that is a later, larger execution-policy change.

## Not Doing

- Do not redesign all Writing Agent execution.
- Do not add a universal write execution engine.
- Do not require UI changes.
- Do not call DeepSeek or generate a chapter.
- Do not add full JSON Schema validation.

## Task 1: RED Tests for Persisted Agent Plan Approval

**Files:**
- Modify: `backend/tests/test_writing_agent_runs.py`

- [ ] Extend `test_agent_run_prepare_longform_chapter_batch_execution_returns_approval_contract` to assert:
  - output includes `agent_plan`
  - output includes `agent_plan_approval_contract`
  - task result persists both objects
  - approval contract includes `agent_plan_approval_contract_hash`
- [ ] Run the targeted test and confirm RED because these fields do not exist yet.

Command:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "prepare_longform_chapter_batch_execution_returns_approval_contract" -q
```

Expected RED:

```text
KeyError: 'agent_plan'
```

## Task 2: RED Tests for Execute Fresh Verification Gate

**Files:**
- Modify: `backend/tests/test_writing_agent_runs.py`

- [ ] Add a test that removes `agent_plan_approval_contract` from the prepared task result and asserts execute returns blocked with `reason == "agent_plan_approval_verification_missing"`.
- [ ] Add a test that tampers persisted `agent_plan.steps[0].params.chapter_index` after prepare and asserts execute returns blocked with `reason == "agent_plan_approval_hash_mismatch"`.
- [ ] Extend the successful execute test to assert output evidence includes `agent_plan_approval_verified`.
- [ ] Run focused tests and confirm RED.

Command:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "execute_longform_chapter_batch" -q
```

Expected RED:

```text
AssertionError or KeyError for missing agent plan approval gate evidence
```

## Task 3: Persist Agent Plan Approval During Prepare

**Files:**
- Modify: `backend/app/services/writing_agent/batch_execution_prepare.py`

- [ ] Import `build_agent_plan_approval_contract`.
- [ ] Build an Agent plan with one write step:
  - `tool_name == "generate_chapter"`
  - `params == {"chapter_index": selected_chapters[0]}`
  - `mutability == "write"`
  - `requires_confirmation is True`
- [ ] Build and persist `agent_plan_approval_contract`.
- [ ] Add `agent_plan_approval_contract_hash` to the Phase61 approval contract payload before hashing.
- [ ] Return and persist `agent_plan` and `agent_plan_approval_contract`.

## Task 4: Fresh Verify Before Batch Execution

**Files:**
- Modify: `backend/app/services/writing_agent/batch_execution.py`
- Modify: `backend/app/services/writing_agent/tool_executor.py`

- [ ] Add optional `agent_plan_tool_metadata_by_name` parameter to `execute_longform_chapter_batch()`.
- [ ] In `_validate_execution_request()`, after existing approval hash checks pass, call `verify_agent_plan_approval_contract()` with:
  - persisted `agent_plan`
  - persisted `agent_plan_approval_contract`
  - persisted approval hash
  - current project id
  - injected tool metadata
- [ ] Block when verifier status is not `ready`.
- [ ] Include verification result in successful output evidence.
- [ ] In `tool_executor.py`, pass `_approval_tool_metadata_by_name(agent_plan)` from the persisted plan context when calling batch execution.

## Task 5: Verification and Report

**Files:**
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-22-phase111-execution-approval-verification-gate.md`

- [ ] Run focused RED/GREEN tests.
- [ ] Run T1 related tests:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "longform_chapter_batch_execution or execute_longform_chapter_batch" -q
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_approval_contract.py backend/tests/test_writing_agent_tool_registry.py -q
```

- [ ] Run hygiene checks:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

- [ ] Write the Phase111 report with exact verification evidence and next phase recommendation.
