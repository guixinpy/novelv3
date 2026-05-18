# Longform Scale Phase 18 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent Athena context boundary construction from loading full chapter content just to compute chapter count and range.

**Architecture:** Keep the context block output stable. Replace the full `ChapterContent` row load with aggregate `count/min/max` over generated chapters.

**Tech Stack:** SQLAlchemy, Pytest.

---

### Task 1: Aggregate Context Boundary

**Files:**
- Modify: `backend/app/prompting/providers/dialog.py`
- Test: `backend/tests/test_athena_dialog.py`

- [x] **Step 1: Write failing SQL-level test**

Create a project with many large chapter contents. Capture SQL statements while calling `build_athena_context_boundary_block`. Assert the block still says `正文：已生成 250 / 目标 300，范围第1章至第250章`, and no SQL statement selects the `chapter_contents.content` column.

- [x] **Step 2: Run test to verify failure**

Run:
- `cd backend; .\.venv\Scripts\python.exe -m pytest tests/test_athena_dialog.py::test_athena_context_boundary_uses_aggregate_chapter_stats -q`

Expected: FAIL because current implementation selects full `ChapterContent` rows, including `content`.

- [x] **Step 3: Implement minimal change**

In `build_athena_context_boundary_block`, replace the chapter `.all()` query with:
- `count(ChapterContent.id)`
- `min(ChapterContent.chapter_index)`
- `max(ChapterContent.chapter_index)`

- [x] **Step 4: Run test to verify pass**

Run the same focused pytest command.

Expected: PASS.

### Task 2: Verification And Commit

**Files:**
- Verify `backend/app/prompting/providers/dialog.py` and `backend/tests/test_athena_dialog.py`.

- [x] **Step 1: Run focused dialog tests**

Run:
- `cd backend; .\.venv\Scripts\python.exe -m pytest tests/test_athena_dialog.py -q`

Expected: PASS.

- [x] **Step 2: Run full verification**

Run:
- `cd backend; .\.venv\Scripts\python.exe -m pytest`
- `cd frontend; npm run test:unit`
- `cd frontend; npm run build`
- `git diff --check`
- exact DeepSeek key scan
- broad secret scan

Expected: all pass; exact key absent; broad scan only contains existing fake sanitizer fixtures.

- [x] **Step 3: Commit**

Commit message: `perf: aggregate athena context boundary stats`
