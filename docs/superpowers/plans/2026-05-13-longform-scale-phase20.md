# Longform Scale Phase 20 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent full retrieval reindex cleanup from loading every existing retrieval chunk id before deletion.

**Architecture:** Keep the public `reindex_project_retrieval` result stable. Replace project-level index cleanup with direct bulk deletes by `project_id`, using the existing `project_id` columns on terms, embeddings, chunks, and documents.

**Tech Stack:** SQLAlchemy, Pytest.

---

### Task 1: Bulk Delete Project Retrieval Index

**Files:**
- Modify: `backend/app/core/athena_retrieval.py`
- Test: `backend/tests/test_athena_retrieval.py`

- [x] **Step 1: Write failing cleanup test**

Add a test that reindexes a project once, captures SQL during a second `reindex_project_retrieval(db, project.id)`, and asserts the second cleanup does not issue `SELECT retrieval_chunks.id ... FROM retrieval_chunks`.

- [x] **Step 2: Run test to verify failure**

Run:
- `cd backend; .\.venv\Scripts\python.exe -m pytest tests/test_athena_retrieval.py::test_reindex_cleanup_deletes_by_project_without_loading_chunk_ids -q`

Expected: FAIL because current `_delete_project_index` loads every chunk id before bulk deletion.

- [x] **Step 3: Implement minimal bulk cleanup**

In `_delete_project_index`, remove the `chunk_ids = [...]` query and delete in this order:
- `RetrievalTerm.project_id == project_id`
- `RetrievalEmbedding.project_id == project_id`
- `RetrievalChunk.project_id == project_id`
- `RetrievalDocument.project_id == project_id`

- [x] **Step 4: Run focused retrieval tests**

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

Commit message: `perf: bulk delete retrieval index`
