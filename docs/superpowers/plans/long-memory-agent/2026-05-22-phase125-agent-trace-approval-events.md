# Phase125 Agent Trace Approval Events Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Include dialog approval decisions in `inspect_agent_trace_audit` so Agent runs can expose a bounded event chain from user approval to tool execution.

**Architecture:** Reuse the existing `agent_trace_audit` tool instead of adding a new Trace/Event store. Phase123 persists `approval_decision` on system dialog messages and includes `agent_run_id`; Phase125 queries those messages for the inspected run and returns sanitized `approval_events`.

**Tech Stack:** SQLAlchemy models (`WritingAgentRun`, `DialogMessage`), existing Writing Agent trace audit service, pytest.

---

## Scope

This phase advances Agentization by turning approval metadata into an Agent-readable trace audit artifact. It intentionally does not add database tables, migrations, frontend pages, or a generic event bus.

## Files

- Modify: `backend/app/services/writing_agent/agent_trace_audit.py`
  - Query system dialog messages for `action_result.data.agent_run_id == run.id`.
  - Extract `action_result.data.approval_decision`.
  - Return sanitized `approval_events` in `inspect_agent_trace_audit(...)`.
  - Do not expose raw `approval_contract_hash`.
- Modify: `backend/tests/test_writing_agent_trace_audit.py`
  - Add a test covering approval event extraction from dialog system action messages.
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-22-phase125-agent-trace-approval-events.md`
  - Record implementation, verification, and reference-project/subagent findings.

## Validation Level

T1:

- Single backend service and focused tests.
- No schema migration and no frontend contract change.

Commands:

- RED/GREEN:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_trace_audit.py::test_inspect_agent_trace_audit_includes_dialog_approval_events_without_raw_hash -q`
- Regression:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_trace_audit.py backend\tests\test_dialogs.py -q`
- Hygiene:
  - `git diff --check`
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`

## Task 1: Failing Test

**Files:**
- Modify: `backend/tests/test_writing_agent_trace_audit.py`

- [ ] **Step 1: Add test**

Add a test that creates a `Dialog`, a `WritingAgentRun` with `dialog_id`, and a system `DialogMessage` containing:

```python
action_result={
    "type": "generate_chapter",
    "status": "generating",
    "data": {
        "agent_run_id": run.id,
        "approval_decision": {
            "kind": "pending_action_decision",
            "pending_action_id": "pending-1",
            "action_type": "generate_chapter",
            "pending_action_type": "generate_chapter",
            "decision": "confirm",
            "decision_comment": "",
            "resolved_at": "2026-05-22T12:00:00+00:00",
            "approval_mode": "single",
            "approval_contract_hash": "approval:secret-hash",
            "approval_contract_version": "phase108.agent_plan_approval_contract.v1",
        },
    },
}
```

Assert:

```python
output = inspect_agent_trace_audit(db_session, project.id, run_id=run.id)

assert output["approval_events"] == [
    {
        "kind": "pending_action_decision",
        "message_id": message.id,
        "action_type": "generate_chapter",
        "pending_action_type": "generate_chapter",
        "decision": "confirm",
        "decision_label": "已确认",
        "approval_mode": "single",
        "approval_contract_bound": True,
        "approval_contract_version": "phase108.agent_plan_approval_contract.v1",
        "resolved_at": "2026-05-22T12:00:00+00:00",
    }
]
assert "approval:secret-hash" not in str(output["approval_events"])
assert output["audit"]["approval_event_count"] == 1
```

- [ ] **Step 2: Run RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_trace_audit.py::test_inspect_agent_trace_audit_includes_dialog_approval_events_without_raw_hash -q
```

Expected: FAIL because `approval_events` is missing.

## Task 2: Minimal Implementation

**Files:**
- Modify: `backend/app/services/writing_agent/agent_trace_audit.py`

- [ ] **Step 1: Import `DialogMessage`**

Add it to the existing model import list.

- [ ] **Step 2: Add `_approval_events_for_run(...)`**

Query by `run.dialog_id`, role `system`, and action_result presence. Filter in Python for:

- `action_result.data.agent_run_id == run.id`
- `action_result.data.approval_decision` is a dict

Return a sanitized list containing only bounded fields and `approval_contract_bound: bool`.

- [ ] **Step 3: Include events in audit output**

In `inspect_agent_trace_audit(...)`:

- Compute `approval_events = _approval_events_for_run(...)`.
- Add `approval_event_count` to `audit`.
- Add top-level `approval_events`.

## Task 3: Verify, Document, Commit

**Files:**
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-22-phase125-agent-trace-approval-events.md`

- [ ] Run targeted test.
- [ ] Run regression subset.
- [ ] Run hygiene checks.
- [ ] Include subagent findings in report.
- [ ] Commit and push:

```powershell
git add backend/app/services/writing_agent/agent_trace_audit.py backend/tests/test_writing_agent_trace_audit.py docs/superpowers/plans/long-memory-agent/2026-05-22-phase125-agent-trace-approval-events.md docs/superpowers/notes/long-memory-agent/2026-05-22-phase125-agent-trace-approval-events.md
git commit -m "feat: include approval events in agent trace audit"
git push origin main
```
