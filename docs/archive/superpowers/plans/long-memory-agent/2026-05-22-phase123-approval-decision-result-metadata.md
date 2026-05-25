# Phase123 Approval Decision Result Metadata Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record the user's pending-action decision as structured metadata in `action_result` so approval-backed tool execution has an auditable decision boundary.

**Architecture:** Keep this phase inside the dialog approval boundary. `resolve_action` already owns the pending-action claim, decision write, task dispatch, response payload, and terminal system message, so it should attach a bounded `approval_decision` object to the same `action_result.data` without changing execution semantics or adding storage tables.

**Tech Stack:** FastAPI, SQLAlchemy, existing dialog API tests, pytest.

---

## Scope

This phase serves the long-memory Writing Agent goal by making approval decisions first-class trace evidence. Phase122 made the pending approval preview visible; Phase123 records what the user decided when the pending action is resolved.

## Files

- Modify: `backend/app/api/dialogs.py`
  - Add a small `_approval_decision_metadata(...)` helper near `resolve_action`.
  - Attach `approval_decision` into `action_result.data`.
  - Persist the full `action_result` on the terminal system message instead of the current minimal `{type, status}` object.
- Modify: `backend/tests/test_dialogs.py`
  - Add assertions that the follow-up chapter approval confirm result includes decision metadata.
  - Add assertions that the terminal system message stores the same bounded metadata.
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-22-phase123-approval-decision-result-metadata.md`
  - Record actual changes, validation evidence, and next phase recommendation.

## Validation Level

T1/T2 hybrid:

- T1 because runtime behavior is localized to one API endpoint and one backend test file.
- T2 subset because the endpoint sits on the dialog approval path used by the Agent tool workflow.

Commands:

- Targeted RED/GREEN:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_chapter_approval_followup_resolve_action_records_decision_metadata -q`
- Backend regression for dialog module:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py -q`
- Hygiene:
  - `git diff --check`
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`

No frontend build is required unless frontend files change.

## Task 1: Add Failing Test

**Files:**
- Modify: `backend/tests/test_dialogs.py`

- [ ] **Step 1: Add a test for approval decision metadata**

Add a test after `test_chapter_approval_followup_dispatches_execute_tool`:

```python
@pytest.mark.asyncio
async def test_chapter_approval_followup_resolve_action_records_decision_metadata(client, db_session):
    project = Project(name="Chapter Approval Decision Metadata")
    db_session.add(project)
    db_session.commit()
    dialog = dialogs_api._get_or_create_dialog(db_session, project.id)

    from app.services.writing_agent.dialog_control_plane import prepare_dialog_agent_run_dispatch

    prepare_dispatch = prepare_dialog_agent_run_dispatch(
        db_session,
        project_id=project.id,
        dialog_id=dialog.id,
        action_type="generate_chapter",
        command_args="2 承接上一章记忆线索",
        action_params={"project_id": project.id, "chapter_index": 2},
    )
    await prepare_dispatch.work(db_session, prepare_dispatch.task)

    pending = db_session.query(PendingAction).filter_by(dialog_id=dialog.id, status="pending").one()

    with patch("app.api.dialogs.LocalTaskRunner.start"):
        response = client.post(
            "/api/v1/dialog/resolve-action",
            json={"action_id": pending.id, "decision": "confirm"},
        )

    assert response.status_code == 200
    action_result = response.json()["action_result"]
    decision = action_result["data"]["approval_decision"]
    assert decision["kind"] == "pending_action_decision"
    assert decision["pending_action_id"] == pending.id
    assert decision["pending_action_type"] == "generate_chapter"
    assert decision["action_type"] == "generate_chapter"
    assert decision["decision"] == "confirm"
    assert decision["approval_mode"] == "single"
    assert decision["approval_contract_hash"] == pending.params["approval_contract_hash"]
    assert decision["approval_contract_version"] == "phase108.agent_plan_approval_contract.v1"
    assert decision["resolved_at"]

    terminal = (
        db_session.query(DialogMessage)
        .filter(DialogMessage.dialog_id == dialog.id, DialogMessage.role == "system")
        .order_by(DialogMessage.created_at.desc())
        .first()
    )
    assert terminal.action_result["data"]["approval_decision"] == decision
```

- [ ] **Step 2: Run the test and confirm RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_chapter_approval_followup_resolve_action_records_decision_metadata -q
```

Expected: FAIL because `approval_decision` is not present in `action_result.data`.

## Task 2: Implement Minimal Metadata Projection

**Files:**
- Modify: `backend/app/api/dialogs.py`

- [ ] **Step 1: Add helper**

Add:

```python
def _approval_decision_metadata(pending: PendingAction, decision: str, action_type: str) -> dict:
    params = pending.params if isinstance(pending.params, dict) else {}
    contract = params.get("approval_contract") if isinstance(params.get("approval_contract"), dict) else {}
    return {
        "kind": "pending_action_decision",
        "pending_action_id": pending.id,
        "action_type": action_type,
        "pending_action_type": pending.type,
        "decision": decision,
        "decision_comment": pending.decision_comment or "",
        "resolved_at": pending.resolved_at.isoformat() if pending.resolved_at else None,
        "approval_mode": "single",
        "approval_contract_hash": params.get("approval_contract_hash"),
        "approval_contract_version": contract.get("version"),
    }
```

- [ ] **Step 2: Attach metadata to result data**

After `result_data` is created and before `_save_message(...)`, add:

```python
result_data["approval_decision"] = _approval_decision_metadata(pending, payload.decision, action_type)
```

- [ ] **Step 3: Persist full action result**

Replace:

```python
_save_message(db, dialog.id, "system", resolve_msg, {"type": action_type, "status": result_data["status"]})
```

With:

```python
_save_message(db, dialog.id, "system", resolve_msg, action_result)
```

## Task 3: Verify and Document

**Files:**
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-22-phase123-approval-decision-result-metadata.md`

- [ ] **Step 1: Run targeted GREEN**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_chapter_approval_followup_resolve_action_records_decision_metadata -q
```

Expected: PASS.

- [ ] **Step 2: Run dialog regression**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py -q
```

Expected: all tests pass.

- [ ] **Step 3: Run hygiene checks**

Run:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

Expected: `git diff --check` exits 0; secret scan returns no matches.

- [ ] **Step 4: Write phase report**

Record:

- Actual changes.
- Validation evidence.
- No novel chapter generated in this phase because this is approval-trace infrastructure.
- Next phase recommendation: start projecting approval decision metadata into trace/event views or extend the same pattern to world-model write approvals.

- [ ] **Step 5: Commit and push**

Run:

```powershell
git status --short
git add backend/app/api/dialogs.py backend/tests/test_dialogs.py docs/superpowers/plans/long-memory-agent/2026-05-22-phase123-approval-decision-result-metadata.md docs/superpowers/notes/long-memory-agent/2026-05-22-phase123-approval-decision-result-metadata.md
git commit -m "feat: record approval decisions in action results"
git push origin main
```
