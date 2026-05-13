# Longform Scale Phase 21 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent longform maintenance diagnostics from selecting full chapter text when it only needs chapter indexes and update timestamps.

**Architecture:** Keep diagnostics payload stable. Narrow `_maintained_chapters` to a column projection of `chapter_index` and `updated_at`; the existing maintenance loop already only reads those fields.

**Tech Stack:** SQLAlchemy, Pytest.

---

### Task 1: Project Maintenance Chapter Rows

**Files:**
- Modify: `backend/app/core/longform_memory.py`
- Test: `backend/tests/test_longform_scale.py`

- [x] **Step 1: Write failing SQL projection test**

Add a test that creates chapters with large content, captures SQL during `get_longform_maintenance_diagnostics`, and asserts the `chapter_contents` SELECT clause does not include `chapter_contents.content`.

- [x] **Step 2: Run test to verify failure**

Run:
- `cd backend; .\.venv\Scripts\python.exe -m pytest tests/test_longform_scale.py::test_longform_maintenance_diagnostics_does_not_select_chapter_content -q`

Expected: FAIL because `_maintained_chapters` currently loads full `ChapterContent` ORM rows.

- [x] **Step 3: Implement minimal projection**

In `_maintained_chapters`, replace the ORM-row query with a column query selecting only:
- `ChapterContent.chapter_index`
- `ChapterContent.updated_at`

Keep the `content != ""` filter and chapter ordering unchanged.

- [x] **Step 4: Run focused longform tests**

Run:
- `cd backend; .\.venv\Scripts\python.exe -m pytest tests/test_longform_scale.py -q`

Expected: PASS.

### Task 2: Verification And Commit

**Files:**
- Verify `backend/app/core/longform_memory.py`, `backend/tests/test_longform_scale.py`, and this plan document.

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

Commit message: `perf: narrow longform maintenance chapter scan`
