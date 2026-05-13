# Longform Scale Phase 19 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent full retrieval reindex from materializing every chapter ORM row before indexing.

**Architecture:** Keep `reindex_project_retrieval` behavior stable while changing `_project_sources` into an iterable source stream. Chapter source queries should project only the columns needed for retrieval documents and use batched iteration so thousand-chapter projects do not build a giant list of chapter objects.

**Tech Stack:** SQLAlchemy, Pytest.

---

### Task 1: Stream Project Retrieval Sources

**Files:**
- Modify: `backend/app/core/athena_retrieval.py`
- Test: `backend/tests/test_athena_retrieval.py`

- [x] **Step 1: Write failing source-stream test**

Add a test that imports `_project_sources`, creates multiple generated chapters, and asserts `_project_sources(db, project.id)` is not a `list`. Iterate the returned value and assert the chapter source refs remain ordered as `chapter:1`, `chapter:2`, `chapter:3`.

- [x] **Step 2: Write failing SQL projection test**

Add a test that captures SQL during `reindex_project_retrieval(db, project.id)`. Assert reindex still indexes all chapters, and the chapter source SELECT clause does not include non-indexing columns such as `word_count`, `model`, `prompt_tokens`, `completion_tokens`, `generation_time`, `temperature`, `created_at`, or `updated_at`.

- [x] **Step 3: Run tests to verify failure**

Run:
- `cd backend; .\.venv\Scripts\python.exe -m pytest tests/test_athena_retrieval.py::test_project_sources_streams_chapters_in_order tests/test_athena_retrieval.py::test_reindex_chapter_source_query_projects_only_index_fields -q`

Expected: FAIL because current `_project_sources` returns a list and the chapter query loads full `ChapterContent` ORM rows.

- [x] **Step 4: Implement minimal streaming source iteration**

In `backend/app/core/athena_retrieval.py`:
- Change `_project_sources` to return an iterator instead of a list.
- Query chapter sources with `with_entities(ChapterContent.id, ChapterContent.chapter_index, ChapterContent.title, ChapterContent.content, ChapterContent.status)`.
- Add `yield_per(50)` to the chapter, memory, and fact source queries.
- Change `_index_sources` type annotation from `list[RetrievalSource]` to an iterable type.
- Keep source ordering and indexed counts unchanged.

- [x] **Step 5: Run focused retrieval tests**

Run:
- `cd backend; .\.venv\Scripts\python.exe -m pytest tests/test_athena_retrieval.py -q`

Expected: PASS.

### Task 2: Verification And Commit

**Files:**
- Verify `backend/app/core/athena_retrieval.py`, `backend/tests/test_athena_retrieval.py`, and this plan document.

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

Commit message: `perf: stream retrieval reindex sources`
