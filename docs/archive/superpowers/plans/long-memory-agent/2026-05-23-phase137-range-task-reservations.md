# Phase137 Range Task Reservations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Treat active `generate_chapter_range` tasks as reserved chapter targets when inferring the next chapter.

**Architecture:** Extend the Phase134 reservation scanner to read `payload.chapter_range.start/end`. Expand the active range into occupied chapter indexes so low-detail continuation skips chapters already covered by batch generation.

**Tech Stack:** FastAPI dialog endpoint, SQLAlchemy models, pytest.

---

## Scope

This phase covers background range tasks only. It does not change batch execution, enqueue behavior, or task cancellation.

## Files

- Modify: `backend/app/api/dialogs.py`
- Modify: `backend/tests/test_dialogs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase137-range-task-reservations.md`

## Validation Level

T1:

- Dialog endpoint test for low-detail continuation with active range task.
- Full `test_dialogs.py` regression because dialog target inference is shared.

Commands:

- Targeted RED/GREEN:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_chat_text_continue_skips_active_chapter_range_task -q`
- Regression subset:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py -q`
- Hygiene:
  - `git diff --check`
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`

## Task 1: Failing Test

- [ ] **Step 1: Add range reservation test**

Seed outline chapters 1-4, generated chapter 1, and an active `generate_chapter_range` task for chapters 2-3. Sending `继续吧` should target chapter 4.

```python
def test_chat_text_continue_skips_active_chapter_range_task(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    db_session.add(Setup(project_id=pid, status="generated", world_building={}, characters=[], core_concept={}))
    db_session.add(Storyline(project_id=pid, status="generated", plotlines=[], foreshadowing=[]))
    db_session.add(Outline(project_id=pid, status="generated", total_chapters=4, chapters=[
        {"chapter_index": 1, "title": "一", "summary": "一"},
        {"chapter_index": 2, "title": "二", "summary": "二"},
        {"chapter_index": 3, "title": "三", "summary": "三"},
        {"chapter_index": 4, "title": "四", "summary": "四"},
    ]))
    db_session.add(ChapterContent(project_id=pid, chapter_index=1, title="一", content="第一章正文", status="generated"))
    db_session.add(BackgroundTask(
        project_id=pid,
        task_type="generate_chapter_range",
        status="running",
        payload={"chapter_range": {"start": 2, "end": 3}},
    ))
    db_session.commit()

    r2 = client.post("/api/v1/dialog/chat", json={"project_id": pid, "input_type": "text", "text": "继续吧"})

    assert r2.status_code == 200
    body = r2.json()
    assert body["pending_action"]["type"] == "preview_chapter"
    assert body["pending_action"]["params"]["chapter_index"] == 4
```

- [ ] **Step 2: Run RED**

Expected: test fails because chapter range tasks are not scanned and chapter 2 is selected.

## Task 2: Minimal Implementation

- [ ] **Step 1: Include range task type**

Update `_active_chapter_task_indexes(...)` query:

```python
BackgroundTask.task_type.in_(("generate_chapter", "generate_chapter_range", "writing_agent_run"))
```

- [ ] **Step 2: Parse chapter ranges**

In `_chapter_indexes_from_task_payload(...)`, allow `action_type` values `None`, `generate_chapter`, and `generate_chapter_range`.

Add:

```python
chapter_range = payload.get("chapter_range") if isinstance(payload.get("chapter_range"), dict) else {}
start = _optional_positive_int(chapter_range.get("start"))
end = _optional_positive_int(chapter_range.get("end"))
if start is not None and end is not None and start <= end:
    indexes.update(range(start, end + 1))
```

Keep existing single chapter and tool param parsing.

## Task 3: Verify, Document, Commit

- [ ] Run targeted test and confirm it passes.
- [ ] Run `backend\tests\test_dialogs.py` regression.
- [ ] Run hygiene checks.
- [ ] Write phase report with RED/GREEN evidence.
- [ ] Commit and push:

```powershell
git add backend/app/api/dialogs.py backend/tests/test_dialogs.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase137-range-task-reservations.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase137-range-task-reservations.md
git commit -m "feat: reserve chapter range tasks"
git push origin main
```
