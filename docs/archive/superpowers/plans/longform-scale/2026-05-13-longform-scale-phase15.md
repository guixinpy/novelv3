# Longform Scale Phase 15 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep Athena's "latest chapter" actions authoritative when chapter summaries are paginated.

**Architecture:** Add a `latest_chapter_index` metadata field to chapter list and workspace bootstrap responses. Store it in Pinia as `chaptersLatestIndex`, then let `AthenaView` prefer that authoritative value over the currently loaded summary page.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, Vue 3, Pinia, Vitest, Pytest.

---

### Task 1: Backend Latest Chapter Metadata

**Files:**
- Modify: `backend/app/api/export.py`
- Modify: `backend/app/services/workspace/bootstrap.py`
- Modify: `backend/app/schemas/workspace.py`
- Test: `backend/tests/test_export.py`
- Test: `backend/tests/test_workspace_bootstrap.py`

- [x] **Step 1: Write failing backend tests**

Assert `GET /chapters` and `/workspace-bootstrap` return `latest_chapter_index: 250` while only returning the first 200 summaries.

- [x] **Step 2: Run tests to verify failure**

Run:
- `cd backend; .\.venv\Scripts\python.exe -m pytest tests/test_export.py::test_list_chapters_defaults_to_bounded_page_with_total tests/test_workspace_bootstrap.py::test_workspace_bootstrap_bounds_chapter_summaries_for_large_projects -q`

Expected: FAIL with missing `latest_chapter_index`.

- [x] **Step 3: Implement metadata**

Use `func.max(ChapterContent.chapter_index)` from the same project-scoped query and include the value in both API payloads. Add `chapters_latest_index` to `WorkspaceBootstrapOut`.

- [x] **Step 4: Run backend tests to verify pass**

Run the same focused pytest command.

Expected: PASS.

### Task 2: Frontend Store And Athena Latest Chapter

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/stores/project.ts`
- Modify: `frontend/src/stores/project.workspace.test.ts`
- Modify: `frontend/src/views/AthenaView.vue`
- Modify: `frontend/src/views/AthenaView.test.ts`

- [x] **Step 1: Write failing frontend tests**

Add store assertions for `chaptersLatestIndex`. Add an AthenaView test where only chapters 1-200 are loaded but API metadata says latest is 250; the conflicts view should pass `latestChapterIndex: 250` to `ConsistencyList`.

- [x] **Step 2: Run tests to verify failure**

Run:
- `cd frontend; npm run test:unit -- src/stores/project.workspace.test.ts src/views/AthenaView.test.ts`

Expected: FAIL because `chaptersLatestIndex` does not exist and Athena still derives latest from the loaded page.

- [x] **Step 3: Implement frontend propagation**

Add optional response metadata types. Store `chaptersLatestIndex`, reset it on project scope changes, update it from bootstrap/list responses, and use it in `AthenaView.latestChapterIndex`.

- [x] **Step 4: Run frontend tests to verify pass**

Run the same focused Vitest command.

Expected: PASS.

### Task 3: Verification And Commit

**Files:**
- Verify all changed files from Tasks 1-2.

- [x] **Step 1: Run focused tests**

Run both focused backend and frontend commands from Tasks 1-2.

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

Commit message: `feat: track authoritative latest chapter`
