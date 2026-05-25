# Phase129 Batch Approval Verification Events Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Use the same sanitized approval verification event model for direct chapter generation and longform chapter batch execution, including blocked contract mismatch paths.

**Architecture:** Extract the Phase128 event helper into a shared `approval_verification_event` module, then use it from both direct chapter execution and batch execution. The event remains an output/projection artifact; verification semantics are unchanged.

**Tech Stack:** Writing Agent execution services, pytest.

---

## Scope

Phase129 covers:

- direct single-chapter blocked mismatch event
- batch execution success event
- shared helper to avoid duplicated event schema

It does not implement a persistent event table or UI display.

## Files

- Create: `backend/app/services/writing_agent/approval_verification_event.py`
- Modify: `backend/app/services/writing_agent/chapter_generation_execution.py`
- Modify: `backend/app/services/writing_agent/batch_execution.py`
- Modify: `backend/tests/test_writing_agent_chapter_generation_execution.py`
- Modify: `backend/tests/test_writing_agent_runs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-22-phase129-batch-approval-verification-events.md`

## Validation Level

T2 subset:

- Execution services across direct chapter and longform batch are affected.

Commands:

- Targeted RED/GREEN:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_chapter_generation_execution.py::test_execute_generate_chapter_with_approval_blocks_stale_contract backend\tests\test_writing_agent_runs.py::test_agent_run_can_execute_approved_longform_chapter_batch_once -q`
- Regression subset:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_chapter_generation_execution.py backend\tests\test_writing_agent_runs.py::test_agent_run_can_execute_approved_longform_chapter_batch_once backend\tests\test_writing_agent_tool_executor.py::test_execute_generate_chapter_with_approval_records_verification_event -q`
- Hygiene:
  - `git diff --check`
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`

## Task 1: Failing Tests

- [ ] **Step 1: Direct blocked mismatch assertion**

In `test_execute_generate_chapter_with_approval_blocks_stale_contract`, assert:

```python
assert output["approval_verification_event"]["event_type"] == "contract_blocked"
assert output["approval_verification_event"]["reason"] == "approval_contract_hash_mismatch"
assert "approval:" not in str(output["approval_verification_event"])
```

- [ ] **Step 2: Batch success assertion**

In `test_agent_run_can_execute_approved_longform_chapter_batch_once`, assert:

```python
assert output["approval_verification_event"] == {
    "event_type": "contract_verified",
    "status": "ready",
    "reason": "approval_contract_verified",
    "approval_contract_bound": True,
    "approval_contract_version": "phase108.agent_plan_approval_contract.v1",
    "write_step_count": 1,
    "tool_contract_drift_count": 0,
}
```

- [ ] **Step 3: Run RED**

Expected:

- stale contract test passes once Phase128 already attached blocked event; if so it documents existing coverage.
- batch success test fails because batch output lacks `approval_verification_event`.

## Task 2: Shared Helper and Batch Output

- [ ] **Step 1: Create shared helper**

Move current event construction into:

```python
def build_approval_verification_event(verification: dict[str, Any]) -> dict[str, Any]:
    ...
```

- [ ] **Step 2: Update direct chapter execution**

Import helper and remove private duplicate.

- [ ] **Step 3: Update batch execution**

Add `approval_verification_event` to:

- blocked `agent_plan_approval_verification` output
- successful `completed` output

## Task 3: Verify, Document, Commit

- [ ] Run targeted tests.
- [ ] Run regression subset.
- [ ] Run hygiene.
- [ ] Write report.
- [ ] Commit:

```powershell
git add backend/app/services/writing_agent/approval_verification_event.py backend/app/services/writing_agent/chapter_generation_execution.py backend/app/services/writing_agent/batch_execution.py backend/tests/test_writing_agent_chapter_generation_execution.py backend/tests/test_writing_agent_runs.py docs/superpowers/plans/long-memory-agent/2026-05-22-phase129-batch-approval-verification-events.md docs/superpowers/notes/long-memory-agent/2026-05-22-phase129-batch-approval-verification-events.md
git commit -m "feat: audit batch approval verification events"
git push origin main
```
