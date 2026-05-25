# Phase128 Contract Verification Events Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Distinguish user approval from system contract verification by adding sanitized approval verification events to tool output and trace audit event chains.

**Architecture:** `execute_generate_chapter_with_approval` already calls `verify_agent_plan_approval_contract` and returns `agent_plan_approval_verification`. Phase128 adds a compact `approval_verification_event` next to that existing data and teaches `inspect_agent_trace_audit` to project it as `contract_verified` / `contract_blocked`.

**Tech Stack:** Writing Agent chapter generation execution service, trace audit projection, pytest.

---

## Scope

This phase does not change approval verification logic. It only adds sanitized evidence:

- success path: `contract_verified`
- blocked path: `contract_blocked`

No raw approval hash should appear in event chain output.

## Files

- Modify: `backend/app/services/writing_agent/chapter_generation_execution.py`
  - Add `_approval_verification_event(...)`.
  - Attach it to success output and blocked verification output.
- Modify: `backend/app/services/writing_agent/agent_trace_audit.py`
  - Read `step.output.approval_verification_event`.
  - Add it to `event_chain`.
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
  - Assert execute tool output includes sanitized verification event on blocked/fake path as appropriate.
- Modify: `backend/tests/test_writing_agent_trace_audit.py`
  - Assert event chain includes `contract_verified` from step output.
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-22-phase128-contract-verification-events.md`

## Validation Level

T1/T2 subset:

- T1 for focused backend services.
- T2 subset because this links tool execution output to trace audit.

Commands:

- Targeted RED/GREEN:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_trace_audit.py::test_inspect_agent_trace_audit_includes_dialog_approval_events_without_raw_hash backend\tests\test_writing_agent_tool_executor.py::test_tool_executor_dispatches_execute_generate_chapter_with_approval -q`
- Regression subset:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_trace_audit.py backend\tests\test_writing_agent_tool_executor.py -q`
- Hygiene:
  - `git diff --check`
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`

## Task 1: Failing Tests

- [ ] **Step 1: Trace audit test**

In `test_inspect_agent_trace_audit_includes_dialog_approval_events_without_raw_hash`, add `approval_verification_event` to the step output:

```python
"approval_verification_event": {
    "event_type": "contract_verified",
    "status": "ready",
    "reason": "approval_contract_verified",
    "approval_contract_bound": True,
    "approval_contract_version": "phase108.agent_plan_approval_contract.v1",
    "write_step_count": 1,
}
```

Expected event type order becomes:

```python
[
    "approval_decision",
    "run_dispatched",
    "tool_step",
    "contract_verified",
    "trace_attached",
    "result_message",
]
```

- [ ] **Step 2: Tool executor test**

The current monkeypatched fake hides real execution service internals, so add assertions only after adapting fake output to include the expected field, or add a dedicated direct unit test for `_approval_verification_event`.

Prefer a direct service test if existing fixtures make real chapter generation too expensive.

- [ ] **Step 3: Run RED**

Expected: trace audit test fails because `contract_verified` is not projected.

## Task 2: Minimal Implementation

- [ ] **Step 1: Add event helper in chapter execution**

Output fields:

- `event_type`
- `status`
- `reason`
- `approval_contract_bound`
- `approval_contract_version`
- `write_step_count`
- `tool_contract_drift_count`

Do not include raw hash.

- [ ] **Step 2: Attach helper output**

- In success generation dict after verification ready.
- In blocked verification output inside `extra`.

- [ ] **Step 3: Project in trace audit**

When a step output has `approval_verification_event`, append sanitized event after the `tool_step` event.

## Task 3: Verify, Document, Commit**

- [ ] Run targeted tests.
- [ ] Run regression subset.
- [ ] Run hygiene.
- [ ] Write report.
- [ ] Commit:

```powershell
git add backend/app/services/writing_agent/chapter_generation_execution.py backend/app/services/writing_agent/agent_trace_audit.py backend/tests/test_writing_agent_trace_audit.py backend/tests/test_writing_agent_tool_executor.py docs/superpowers/plans/long-memory-agent/2026-05-22-phase128-contract-verification-events.md docs/superpowers/notes/long-memory-agent/2026-05-22-phase128-contract-verification-events.md
git commit -m "feat: audit approval contract verification events"
git push origin main
```
