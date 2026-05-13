# Longform Scale Phase 22 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent longform memory rebuild from selecting chapter generation metadata that is not used to build memory layers.

**Architecture:** Keep memory rebuild output stable. Narrow `_chapters` to the fields used by `_chapter_memory`, `_range_memory`, and `_global_memory`: chapter index, title, content, word count, and status.

**Tech Stack:** SQLAlchemy, Pytest.

---

### Task 1: Project Rebuild Chapter Rows

**Files:**
- Modify: `backend/app/core/longform_memory.py`
- Test: `backend/tests/test_longform_scale.py`

- [x] **Step 1: Write failing SQL projection test**

Add a test that captures SQL during `rebuild_longform_memory`. Assert the rebuild still creates chapter, arc, volume, and global memories, and the `chapter_contents` SELECT clause does not include generation metadata columns: `model`, `prompt_tokens`, `completion_tokens`, `generation_time`, `temperature`, `created_at`, or `updated_at`.

- [x] **Step 2: Run test to verify failure**

Run:
- `cd backend; .\.venv\Scripts\python.exe -m pytest tests/test_longform_scale.py::test_rebuild_longform_memory_projects_only_memory_fields -q`

Expected: FAIL because `_chapters` currently loads full `ChapterContent` ORM rows.

- [x] **Step 3: Implement minimal projection**

In `_chapters`, replace the ORM-row query with a column query selecting only:
- `ChapterContent.chapter_index`
- `ChapterContent.title`
- `ChapterContent.content`
- `ChapterContent.word_count`
- `ChapterContent.status`

Update narrow helper type annotations from `list[ChapterContent]` to `list[Any]` where they operate on the projected rows.

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

Commit message: `perf: narrow longform memory rebuild scan`
