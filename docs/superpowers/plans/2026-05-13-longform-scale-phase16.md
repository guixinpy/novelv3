# Longform Scale Phase 16 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent long-form exports from silently truncating chapters after chapter 100.

**Architecture:** Keep the export endpoint and frontend caller shape stable. Change the backend request model so omitted `chapter_range` means "export all chapters"; retain explicit `[start, end]` ranges for partial exports.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, Pytest.

---

### Task 1: Export Defaults

**Files:**
- Modify: `backend/app/api/export.py`
- Test: `backend/tests/test_export.py`

- [x] **Step 1: Write failing tests**

Add tests that create chapters 1, 100, and 150:
- Default export includes chapter 150.
- Explicit `chapter_range: [1, 100]` still excludes chapter 150.

- [x] **Step 2: Run tests to verify failure**

Run:
- `cd backend; .\.venv\Scripts\python.exe -m pytest tests/test_export.py::test_export_markdown_defaults_to_all_chapters tests/test_export.py::test_export_markdown_honors_explicit_chapter_range -q`

Expected: default export test fails because chapter 150 is omitted.

- [x] **Step 3: Implement minimal backend change**

Change `ExportRequest.chapter_range` from default `[1, 100]` to `None`. In `export_project`, apply chapter index filters only when a valid range is supplied.

- [x] **Step 4: Run tests to verify pass**

Run the same focused pytest command.

Expected: PASS.

### Task 2: Verification And Commit

**Files:**
- Verify `backend/app/api/export.py` and `backend/tests/test_export.py`.

- [x] **Step 1: Run focused export tests**

Run:
- `cd backend; .\.venv\Scripts\python.exe -m pytest tests/test_export.py -q`

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

Commit message: `fix: export all chapters by default`
