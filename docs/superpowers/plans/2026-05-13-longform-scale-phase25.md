# Longform Scale Phase 25 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent chapter generation from loading all chapter rows just to update project word count.

**Architecture:** Keep chapter generation behavior stable. Replace the post-generation Python sum over all `ChapterContent` ORM rows with a database aggregate `sum(word_count)`.

**Tech Stack:** FastAPI, SQLAlchemy, Pytest.

---

### Task 1: Aggregate Chapter Generation Word Count

**Files:**
- Modify: `backend/app/api/chapters.py`
- Test: `backend/tests/test_chapters.py`

- [x] **Step 1: Write failing SQL regression test**

Add a test that creates many existing chapters, generates one chapter, captures SQL, and asserts generation does not issue an unbounded full-row `SELECT chapter_contents.id ... FROM chapter_contents WHERE chapter_contents.project_id = ?` without a `chapter_index` predicate.

- [x] **Step 2: Run test to verify failure**

Run:
- `cd backend; .\.venv\Scripts\python.exe -m pytest tests/test_chapters.py::test_generate_chapter_reconciles_word_count_with_aggregate_query -q`

Expected: FAIL because current generation loads every chapter row to sum `word_count` in Python.

- [x] **Step 3: Implement aggregate word count**

In `create_or_replace_chapter`, replace the Python sum over `db.query(ChapterContent).filter(...).all()` with:
- `db.query(func.coalesce(func.sum(ChapterContent.word_count), 0)).filter(...).scalar()`

- [x] **Step 4: Run focused chapter tests**

Run:
- `cd backend; .\.venv\Scripts\python.exe -m pytest tests/test_chapters.py -q`

Expected: PASS.

### Task 2: Verification And Commit

**Files:**
- Verify `backend/app/api/chapters.py`, `backend/tests/test_chapters.py`, and this plan document.

- [x] **Step 1: Run full verification**

Run:
- `cd backend; .\.venv\Scripts\python.exe -m pytest`
- `cd frontend; npm run test:unit`
- `cd frontend; npx vue-tsc --noEmit`
- `cd frontend; npm run build`
- `git diff --check`
- exact DeepSeek key scan
- broad secret scan

Expected: all pass; exact key absent; broad scan only contains existing fake sanitizer fixtures.

- [x] **Step 2: Commit**

Commit message: `perf: aggregate chapter generation word count`
