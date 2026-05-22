# Phase126 Dialog Event Chain Links Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Link the dialog approval decision message to the spawned `WritingAgentRun` and expose both approval/result dialog messages in trace audit output.

**Architecture:** Keep Phase126 as a small relationship repair. `resolve_action(confirm)` already creates the run before saving the system confirmation message; after `_save_message(...)` returns, use `action_result.data.agent_run_id` to set `WritingAgentRun.request_message_id`. `inspect_agent_trace_audit` can then use `run.request_message_id` and `run.response_message_id` for dialog event summaries.

**Tech Stack:** FastAPI dialog API, SQLAlchemy models, existing trace audit service, pytest.

---

## Scope

This phase continues Phase125. It does not add a new event table or frontend UI. It strengthens existing entity links:

- approval message -> `WritingAgentRun.request_message_id`
- completion message -> `WritingAgentRun.response_message_id` already exists
- audit output -> `dialog_events`

## Files

- Modify: `backend/app/api/dialogs.py`
  - Save the resolve system message to a variable.
  - If `result_data.agent_run_id` exists, set `WritingAgentRun.request_message_id` to the system message id.
- Modify: `backend/app/services/writing_agent/agent_trace_audit.py`
  - Add `dialog_events` summary with approval and result message ids/statuses.
- Modify: `backend/tests/test_dialogs.py`
  - Assert confirm path stores `run.request_message_id`.
- Modify: `backend/tests/test_writing_agent_trace_audit.py`
  - Assert trace audit returns approval/result dialog event summaries.
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-22-phase126-dialog-event-chain-links.md`

## Validation Level

T1/T2 subset:

- T1 for one API relationship and one read projection.
- T2 subset because dialog confirmation and trace audit cross service boundaries.

Commands:

- Targeted:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_resolve_chapter_action_confirm_dispatches_prepare_tool backend\tests\test_writing_agent_trace_audit.py::test_inspect_agent_trace_audit_includes_dialog_approval_events_without_raw_hash -q`
- Regression:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py backend\tests\test_writing_agent_trace_audit.py -q`
- Hygiene:
  - `git diff --check`
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`

## Task 1: Failing Tests

**Files:**
- Modify: `backend/tests/test_dialogs.py`
- Modify: `backend/tests/test_writing_agent_trace_audit.py`

- [ ] **Step 1: Add request message assertion**

In `test_resolve_chapter_action_confirm_dispatches_prepare_tool`, after loading `run`, query the latest system message and assert:

```python
decision_message = (
    db_session.query(DialogMessage)
    .filter(DialogMessage.dialog_id == run.dialog_id, DialogMessage.role == "system")
    .order_by(DialogMessage.created_at.desc(), DialogMessage.id.desc())
    .first()
)
assert run.request_message_id == decision_message.id
assert decision_message.action_result["data"]["agent_run_id"] == run.id
```

- [ ] **Step 2: Add dialog event assertions**

In `test_inspect_agent_trace_audit_includes_dialog_approval_events_without_raw_hash`, set `run.request_message_id = message.id`, create a second result system message, set `run.response_message_id = result_message.id`, and assert:

```python
assert output["dialog_events"] == {
    "approval_message": {
        "id": message.id,
        "role": "system",
        "action_type": "generate_chapter",
        "action_status": "generating",
    },
    "result_message": {
        "id": result_message.id,
        "role": "system",
        "action_type": "generate_chapter",
        "action_status": "success",
    },
}
```

- [ ] **Step 3: Run RED**

Run targeted command. Expected failures:

- `run.request_message_id` is `None`.
- `dialog_events` is missing.

## Task 2: Implement Link and Projection

**Files:**
- Modify: `backend/app/api/dialogs.py`
- Modify: `backend/app/services/writing_agent/agent_trace_audit.py`

- [ ] **Step 1: Persist request message link**

Change `_save_message(...)` in `resolve_action` to:

```python
decision_message = _save_message(db, dialog.id, "system", resolve_msg, action_result)
_link_run_request_message(db, result_data.get("agent_run_id"), decision_message.id)
```

Add helper:

```python
def _link_run_request_message(db: Session, run_id: object, message_id: str) -> None:
    if not run_id:
        return
    run = db.query(WritingAgentRun).filter(WritingAgentRun.id == str(run_id)).first()
    if run is None:
        return
    run.request_message_id = message_id
    db.add(run)
    db.commit()
```

- [ ] **Step 2: Add dialog event projection**

In `agent_trace_audit.py`, query `DialogMessage` by `run.request_message_id` and `run.response_message_id`, summarize id/role/action type/action status only.

## Task 3: Verify, Document, Commit

- [ ] Run targeted tests.
- [ ] Run regression subset.
- [ ] Run hygiene checks.
- [ ] Write phase report.
- [ ] Commit:

```powershell
git add backend/app/api/dialogs.py backend/app/services/writing_agent/agent_trace_audit.py backend/tests/test_dialogs.py backend/tests/test_writing_agent_trace_audit.py docs/superpowers/plans/long-memory-agent/2026-05-22-phase126-dialog-event-chain-links.md docs/superpowers/notes/long-memory-agent/2026-05-22-phase126-dialog-event-chain-links.md
git commit -m "feat: link dialog approval messages to agent runs"
git push origin main
```
