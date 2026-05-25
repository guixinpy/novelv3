# Phase139 Conflict Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve chapter target conflict details after approval and expose them through action result view and agent trace audit.

**Architecture:** Reuse the existing approval decision metadata path. Copy a sanitized `chapter_target_conflict` object from pending params into `approval_decision`, render a concise detail row, and project the same object into `inspect_agent_trace_audit` approval events and event chain.

**Tech Stack:** FastAPI dialog approval flow, action result view service, agent trace audit service, pytest.

---

## Scope

This phase does not change conflict detection or frontend pending warning behavior. It only keeps conflict source information auditable after the user confirms or otherwise resolves an action.

## Files

- Modify: `backend/app/api/dialogs.py`
- Modify: `backend/app/services/actions/action_result_view.py`
- Modify: `backend/app/services/writing_agent/agent_trace_audit.py`
- Modify: `backend/tests/test_dialogs.py`
- Modify: `backend/tests/test_writing_agent_trace_audit.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase139-conflict-audit.md`

## Validation Level

T1:

- Dialog approval endpoint test for metadata and result view.
- Trace audit test for approval event and event chain projection.
- Regression on affected backend test files.

Commands:

- Targeted RED/GREEN:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_resolve_chapter_conflict_confirmation_records_decision_metadata backend\tests\test_writing_agent_trace_audit.py::test_inspect_agent_trace_audit_includes_dialog_approval_events_without_raw_hash -q`
- Regression:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py backend\tests\test_writing_agent_trace_audit.py -q`
- Hygiene:
  - `git diff --check`
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`

## Task 1: Failing Tests

- [x] **Step 1: Add dialog approval metadata test**

Add to `backend/tests/test_dialogs.py`:

```python
def test_resolve_chapter_conflict_confirmation_records_decision_metadata(client, db_session):
    project_id = client.post("/api/v1/projects", json={"name": "Chapter Conflict Audit"}).json()["id"]
    db_session.add(
        BackgroundTask(
            project_id=project_id,
            task_type="generate_chapter_range",
            status="running",
            payload={"chapter_range": {"start": 2, "end": 3}},
        )
    )
    db_session.commit()
    pending = client.post(
        "/api/v1/dialog/chat",
        json={
            "project_id": project_id,
            "input_type": "command",
            "command_name": "chapter",
            "command_args": "2",
        },
    ).json()["pending_action"]

    with patch("app.api.dialogs.LocalTaskRunner.start"):
        response = client.post(
            "/api/v1/dialog/resolve-action",
            json={"action_id": pending["id"], "decision": "confirm"},
        )

    assert response.status_code == 200
    decision = response.json()["action_result"]["data"]["approval_decision"]
    assert decision["chapter_target_conflict"] == {
        "status": "reserved",
        "chapter_index": 2,
        "reason": "pending_or_running_generation",
        "source": "range_task",
        "source_label": "批量生成任务",
    }
    detail_items = response.json()["action_result_view"]["detail_items"]
    assert {"label": "章节冲突", "value": "批量生成任务"} in detail_items
```

- [x] **Step 2: Extend trace audit test**

In `test_inspect_agent_trace_audit_includes_dialog_approval_events_without_raw_hash`, add `chapter_target_conflict` to fixture approval decision and expect it in:

- `output["approval_events"][0]["chapter_target_conflict"]`
- `output["event_chain"][0]["chapter_target_conflict"]`

Use this object:

```python
{
    "status": "reserved",
    "chapter_index": 2,
    "reason": "pending_or_running_generation",
    "source": "range_task",
    "source_label": "批量生成任务",
}
```

- [x] **Step 3: Run RED**

Expected:

- Dialog approval decision lacks `chapter_target_conflict`.
- Result view lacks `章节冲突`.
- Trace audit does not project conflict object.

## Task 2: Minimal Implementation

- [x] **Step 1: Sanitize conflict metadata in `dialogs.py`**

Add helper:

```python
def _approval_chapter_target_conflict(params: dict) -> dict | None:
    conflict = params.get("chapter_target_conflict") if isinstance(params.get("chapter_target_conflict"), dict) else None
    if not conflict or conflict.get("status") != "reserved":
        return None
    chapter_index = _optional_positive_int(conflict.get("chapter_index") or params.get("chapter_index"))
    if chapter_index is None:
        return None
    source = str(conflict.get("source") or "").strip()
    source_label = str(conflict.get("source_label") or "").strip()
    return {
        "status": "reserved",
        "chapter_index": chapter_index,
        "reason": str(conflict.get("reason") or "pending_or_running_generation"),
        "source": source,
        "source_label": source_label,
    }
```

In `_approval_decision_metadata(...)`, if helper returns a value, set `metadata["chapter_target_conflict"]`.

- [x] **Step 2: Render action result view row**

In `action_result_view._detail_items(...)`, when `approval_decision.chapter_target_conflict.status == "reserved"`, append:

```python
{"label": "章节冲突", "value": source_label or "已占用"}
```

- [x] **Step 3: Project trace audit conflict**

In `agent_trace_audit.py`, add `_chapter_target_conflict_summary(...)` and call it from `_approval_event_summary(...)`.

Add the conflict object to `chain_event` in `_event_chain(...)` when present.

Do not include task IDs or approval hashes.

## Task 3: Verify, Document, Commit

- [x] Run targeted tests and confirm they pass.
- [x] Run regression subset.
- [x] Run hygiene checks.
- [x] Write phase report with RED/GREEN evidence.
- [ ] Commit and push:

```powershell
git add backend/app/api/dialogs.py backend/app/services/actions/action_result_view.py backend/app/services/writing_agent/agent_trace_audit.py backend/tests/test_dialogs.py backend/tests/test_writing_agent_trace_audit.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase139-conflict-audit.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase139-conflict-audit.md
git commit -m "feat: audit chapter conflict decisions"
git push origin main
```
