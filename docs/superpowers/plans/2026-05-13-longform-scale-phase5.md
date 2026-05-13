# Longform Scale Phase 5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give local background tasks a durable chapter-range progress contract so long-running thousand-chapter jobs can resume from a known checkpoint.

**Architecture:** Do not introduce Celery or schema migrations in this phase. Store range metadata in `BackgroundTask.payload` and progress checkpoints in `BackgroundTask.result`, then expose service methods that future analysis/indexing jobs can call consistently.

**Tech Stack:** FastAPI existing background task model, SQLAlchemy, pytest.

---

## File Structure

- Modify `backend/app/services/tasks/background_task_service.py`: add range task creation, progress checkpointing, and retry creation.
- Modify `backend/app/api/background_tasks_api.py`: include payload in task detail responses for range/resume transparency.
- Modify `backend/tests/test_background.py`: add service and API coverage.

## Success Criteria

- A range task stores `chapter_range.start`, `chapter_range.end`, and optional `idempotency_key` in payload.
- Marking chapter progress updates `result.progress.completed_chapter_indexes`, `next_chapter_index`, `completed_count`, `total_count`, and `can_resume`.
- Retrying a failed range task creates a pending task that references the original task and resumes from `next_chapter_index`.
- Existing background lifecycle tests continue to pass.

## Task 1: Range Task Progress Contract

**Files:**
- Modify: `backend/app/services/tasks/background_task_service.py`
- Test: `backend/tests/test_background.py`

- [x] **Step 1: Write failing service test**

Add a test that creates a range task for chapters 1-5, marks chapters 1 and 2 complete, and asserts `next_chapter_index == 3`.

- [x] **Step 2: Run focused test**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background.py -v
```

Expected: FAIL because range helpers do not exist.

- [x] **Step 3: Implement service helpers**

Add:

- `create_chapter_range(...)`
- `mark_range_progress(task_id, completed_chapter_index)`
- internal helpers for range validation and progress assembly.

- [x] **Step 4: Run focused test**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background.py -v
```

Expected: PASS.

## Task 2: Retry From Checkpoint

**Files:**
- Modify: `backend/app/services/tasks/background_task_service.py`
- Test: `backend/tests/test_background.py`

- [x] **Step 1: Write failing retry test**

Create a failed range task with progress through chapter 2, call `create_retry_from_failed(task.id)`, and assert the retry task is pending, references `retry_of_task_id`, and has `resume_from_chapter_index == 3`.

- [x] **Step 2: Run focused test**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background.py -v
```

Expected: FAIL because retry helper does not exist.

- [x] **Step 3: Implement retry helper**

Add `create_retry_from_failed(task_id)` and reject retry for non-failed/non-cancelled tasks.

- [x] **Step 4: Run focused test**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background.py -v
```

Expected: PASS.

## Task 3: API Transparency

**Files:**
- Modify: `backend/app/api/background_tasks_api.py`
- Test: `backend/tests/test_background.py`

- [x] **Step 1: Write failing API test**

Create a range task, call `GET /api/v1/background-tasks/{task_id}`, and assert response contains `payload.chapter_range`.

- [x] **Step 2: Run focused test**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background.py -v
```

Expected: FAIL because task detail omits payload.

- [x] **Step 3: Include payload in detail response**

Return `payload: task.payload or {}` from the detail endpoint.

- [x] **Step 4: Run focused test**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background.py -v
```

Expected: PASS.

## Task 4: Verification and Commit

- [x] **Step 1: Run background tests**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background.py -v
```

- [x] **Step 2: Run backend tests**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests -v
```

- [x] **Step 3: Check hygiene**

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9_-]{20,}" backend docs frontend .agents
git status --short
```

- [x] **Step 4: Commit**

```powershell
git add backend docs/superpowers/plans/2026-05-13-longform-scale-phase5.md
git commit -m "feat: add resumable range task progress"
```
