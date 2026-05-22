# Phase135 Explicit Chapter Conflict Warning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When a user explicitly asks for a chapter that is already pending or running, keep the explicit chapter target but show a confirmation warning.

**Architecture:** Reuse the reserved chapter target detection from Phase134. For explicit chapter requests, do not skip to another chapter; instead attach a sanitized `chapter_target_conflict` object to pending params and let `action_description` append a warning.

**Tech Stack:** Dialog endpoint, action descriptions, pytest.

---

## Scope

This phase handles explicit chapter conflicts only. Low-detail inferred continuation already skips reserved targets from Phase134.

## Files

- Modify: `backend/app/api/dialogs.py`
- Modify: `backend/app/services/actions/descriptions.py`
- Modify: `backend/tests/test_dialogs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-22-phase135-explicit-chapter-conflict-warning.md`

## Validation Level

T1:

- Dialog endpoint test for explicit command conflict.
- Full `test_dialogs.py` regression.

Commands:

- Targeted RED/GREEN:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_chapter_command_explicit_reserved_target_adds_conflict_warning -q`
- Regression subset:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py -q`
- Hygiene:
  - `git diff --check`
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`

## Task 1: Failing Test

- [ ] **Step 1: Add explicit conflict test**

Seed outline chapters 1-2 and an active task for chapter 2. Run `/chapter 2` and assert:

- pending action still targets chapter 2.
- pending params include `chapter_target_conflict`.
- description warns about an existing pending/running chapter target.

```python
def test_chapter_command_explicit_reserved_target_adds_conflict_warning(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    db_session.add(Outline(project_id=pid, status="generated", total_chapters=2, chapters=[
        {"chapter_index": 1, "title": "一", "summary": "一"},
        {"chapter_index": 2, "title": "二", "summary": "二"},
    ]))
    db_session.add(BackgroundTask(
        project_id=pid,
        task_type="writing_agent_run",
        status="running",
        payload={"action_type": "generate_chapter", "tools": [{"params": {"chapter_index": 2}}]},
    ))
    db_session.commit()

    r2 = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "command",
        "command_name": "chapter",
        "command_args": "2",
    })

    assert r2.status_code == 200
    pending = r2.json()["pending_action"]
    assert pending["params"]["chapter_index"] == 2
    assert pending["params"]["chapter_target_conflict"] == {
        "status": "reserved",
        "chapter_index": 2,
        "reason": "pending_or_running_generation",
    }
    assert "已有待确认或运行中的生成任务" in pending["description"]
```

- [ ] **Step 2: Run RED**

Expected: params have no conflict object and description has no warning.

## Task 2: Minimal Implementation

- [ ] **Step 1: Add conflict helper in `dialogs.py`**

```python
def _chapter_target_conflict(chapter_index: int) -> dict[str, object]:
    return {
        "status": "reserved",
        "chapter_index": chapter_index,
        "reason": "pending_or_running_generation",
    }
```

- [ ] **Step 2: Mark explicit conflicts**

In `_chapter_action_params_for_project(...)`, when `parse_chapter_index(command_args)` returns a chapter:

```python
if explicit_chapter_index in _reserved_chapter_indexes(db, project_id):
    params["chapter_target_conflict"] = _chapter_target_conflict(explicit_chapter_index)
```

Preserve `chapter_index_source = "explicit_user"`.

- [ ] **Step 3: Append description warning**

In `action_description(...)`, for `preview_chapter` and `generate_chapter`, append:

```text
 注意：第N章已有待确认或运行中的生成任务，请确认是否仍要继续。
```

only when `chapter_target_conflict.status == "reserved"`.

## Task 3: Verify, Document, Commit

- [ ] Run targeted test and confirm it passes.
- [ ] Run `backend\tests\test_dialogs.py` regression.
- [ ] Run hygiene checks.
- [ ] Write phase report with RED/GREEN evidence.
- [ ] Commit and push:

```powershell
git add backend/app/api/dialogs.py backend/app/services/actions/descriptions.py backend/tests/test_dialogs.py docs/superpowers/plans/long-memory-agent/2026-05-22-phase135-explicit-chapter-conflict-warning.md docs/superpowers/notes/long-memory-agent/2026-05-22-phase135-explicit-chapter-conflict-warning.md
git commit -m "feat: warn on explicit chapter conflicts"
git push origin main
```
