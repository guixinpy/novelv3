# Phase134 Reserved Chapter Targets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Avoid selecting a chapter that already has a pending approval or active generation task when inferring the next unwritten chapter.

**Architecture:** Keep the reservation logic inside dialog target inference. Treat generated chapters, pending chapter actions, and active chapter generation tasks as occupied targets, then select the first outline chapter not occupied.

**Tech Stack:** FastAPI dialog endpoint, SQLAlchemy models, pytest.

---

## Scope

This phase reduces duplicate chapter generation caused by repeated low-detail continuation requests. It does not implement task cancellation, locks, or database constraints.

## Files

- Modify: `backend/app/api/dialogs.py`
- Modify: `backend/tests/test_dialogs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-22-phase134-reserved-chapter-targets.md`

## Validation Level

T1:

- Dialog endpoint tests for reserved pending action and active task cases.
- Full `test_dialogs.py` regression.

Commands:

- Targeted RED/GREEN:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_chat_text_continue_skips_reserved_pending_chapter backend\tests\test_dialogs.py::test_chat_text_continue_skips_active_chapter_task -q`
- Regression subset:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py -q`
- Hygiene:
  - `git diff --check`
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`

## Task 1: Failing Tests

- [ ] **Step 1: Add pending reservation test**

Seed outline chapters 1-3, generated chapter 1, and a separate dialog pending chapter action for chapter 2. Sending `继续吧` should infer chapter 3.

```python
def test_chat_text_continue_skips_reserved_pending_chapter(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    db_session.add(Setup(project_id=pid, status="generated", world_building={}, characters=[], core_concept={}))
    db_session.add(Storyline(project_id=pid, status="generated", plotlines=[], foreshadowing=[]))
    db_session.add(Outline(project_id=pid, status="generated", total_chapters=3, chapters=[
        {"chapter_index": 1, "title": "一", "summary": "一"},
        {"chapter_index": 2, "title": "二", "summary": "二"},
        {"chapter_index": 3, "title": "三", "summary": "三"},
    ]))
    db_session.add(ChapterContent(project_id=pid, chapter_index=1, title="一", content="第一章正文", status="generated"))
    other_dialog = Dialog(project_id=pid, dialog_type="athena", state="pending_action")
    db_session.add(other_dialog)
    db_session.flush()
    db_session.add(PendingAction(
        dialog_id=other_dialog.id,
        type="preview_chapter",
        params={"project_id": pid, "chapter_index": 2},
        status="pending",
    ))
    db_session.commit()

    r2 = client.post("/api/v1/dialog/chat", json={"project_id": pid, "input_type": "text", "text": "继续吧"})

    assert r2.status_code == 200
    assert r2.json()["pending_action"]["params"]["chapter_index"] == 3
```

- [ ] **Step 2: Add active task reservation test**

Seed outline chapters 1-3, generated chapter 1, and an active `writing_agent_run` task targeting chapter 2. Sending `继续吧` should infer chapter 3.

```python
def test_chat_text_continue_skips_active_chapter_task(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    db_session.add(Setup(project_id=pid, status="generated", world_building={}, characters=[], core_concept={}))
    db_session.add(Storyline(project_id=pid, status="generated", plotlines=[], foreshadowing=[]))
    db_session.add(Outline(project_id=pid, status="generated", total_chapters=3, chapters=[
        {"chapter_index": 1, "title": "一", "summary": "一"},
        {"chapter_index": 2, "title": "二", "summary": "二"},
        {"chapter_index": 3, "title": "三", "summary": "三"},
    ]))
    db_session.add(ChapterContent(project_id=pid, chapter_index=1, title="一", content="第一章正文", status="generated"))
    db_session.add(BackgroundTask(
        project_id=pid,
        task_type="writing_agent_run",
        status="running",
        payload={"action_type": "generate_chapter", "tools": [{"params": {"chapter_index": 2}}]},
    ))
    db_session.commit()

    r2 = client.post("/api/v1/dialog/chat", json={"project_id": pid, "input_type": "text", "text": "继续吧"})

    assert r2.status_code == 200
    assert r2.json()["pending_action"]["params"]["chapter_index"] == 3
```

- [ ] **Step 3: Run RED**

Expected: both tests fail because inference still selects chapter 2.

## Task 2: Minimal Implementation

- [ ] **Step 1: Import `BackgroundTask`**

Add `BackgroundTask` to the `app.models` import in `backend/app/api/dialogs.py`.

- [ ] **Step 2: Add reserved target helpers**

Add:

```python
ACTIVE_TARGET_STATUSES = {"pending", "running", "generating"}

def _reserved_chapter_indexes(db: Session, project_id: str) -> set[int]:
    return _pending_chapter_action_indexes(db, project_id) | _active_chapter_task_indexes(db, project_id)
```

Implement `_pending_chapter_action_indexes(...)` by scanning pending `PendingAction` rows with type `preview_chapter` or `generate_chapter`, checking `params.project_id`, and reading `params.chapter_index`.

Implement `_active_chapter_task_indexes(...)` by scanning active `BackgroundTask` rows for the project with task types `generate_chapter` or `writing_agent_run`, reading:

- `payload.action_params.chapter_index`
- `payload.tools[*].params.chapter_index`

- [ ] **Step 3: Skip reserved chapters during inference**

Update `_first_unwritten_outline_chapter_index(...)`:

```python
occupied = _generated_chapter_indexes(db, project_id) | _reserved_chapter_indexes(db, project_id)
for chapter_index in _outline_chapter_indexes(db, project_id):
    if chapter_index not in occupied:
        return chapter_index
if occupied:
    return max(occupied) + 1
return None
```

Add `_optional_positive_int(...)` to sanitize JSON values.

## Task 3: Verify, Document, Commit

- [ ] Run targeted tests and confirm they pass.
- [ ] Run `backend\tests\test_dialogs.py` regression.
- [ ] Run hygiene checks.
- [ ] Write phase report with RED/GREEN evidence.
- [ ] Commit and push:

```powershell
git add backend/app/api/dialogs.py backend/tests/test_dialogs.py docs/superpowers/plans/long-memory-agent/2026-05-22-phase134-reserved-chapter-targets.md docs/superpowers/notes/long-memory-agent/2026-05-22-phase134-reserved-chapter-targets.md
git commit -m "feat: skip reserved chapter targets"
git push origin main
```
