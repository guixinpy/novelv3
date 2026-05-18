# Longform Scale Phase 13 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent thousand-chapter projects from cold-loading every chapter summary by default.

**Architecture:** Keep the existing chapter summary response shape compatible by preserving `chapters`, but add pagination metadata and a default server-side limit. Workspace bootstrap uses the same bounded chapter summary page, and the project store records the metadata for later pagination UI.

**Tech Stack:** FastAPI query params, SQLAlchemy count/offset/limit, Pydantic schemas, pytest, TypeScript, Pinia, Vitest.

---

## File Structure

- Modify `backend/app/api/export.py`: paginate `GET /chapters`.
- Modify `backend/app/services/workspace/bootstrap.py`: bound bootstrap chapter summaries.
- Modify `backend/app/schemas/workspace.py`: expose bootstrap chapter pagination metadata.
- Modify `backend/tests/test_export.py`: cover default and explicit chapter pages.
- Modify `backend/tests/test_workspace_bootstrap.py`: cover bounded bootstrap chapters.
- Modify `frontend/src/api/types.ts`: add `ChapterListResponse` and bootstrap chapter metadata.
- Modify `frontend/src/api/client.ts`: accept `listChapters` pagination params.
- Modify `frontend/src/stores/project.ts`: store `chaptersTotal`, `chaptersOffset`, `chaptersLimit`, `chaptersHasMore`.
- Modify `frontend/src/stores/project.workspace.test.ts`: cover metadata from `loadChapters` and bootstrap.

## Success Criteria

- `GET /projects/{id}/chapters` defaults to at most 200 summaries and returns `total`, `offset`, `limit`, `has_more`.
- Explicit `offset`/`limit` requests return the requested page in chapter order.
- Workspace bootstrap returns at most 200 chapter summaries and the same metadata.
- Existing clients that read only `chapters` keep working.
- Project store keeps chapter pagination metadata for future UI paging.
- Focused backend/frontend tests, full backend/frontend tests, build, diff hygiene, and sensitive-key scans pass before commit.

## Task 1: Backend Chapter Pagination

**Files:**
- Modify: `backend/app/api/export.py`
- Modify: `backend/app/services/workspace/bootstrap.py`
- Modify: `backend/app/schemas/workspace.py`
- Test: `backend/tests/test_export.py`
- Test: `backend/tests/test_workspace_bootstrap.py`

- [x] **Step 1: Write failing backend tests**

Add tests for default 200-row chapter list, explicit page retrieval, and workspace bootstrap metadata.

- [x] **Step 2: Verify RED**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_export.py::test_list_chapters_defaults_to_bounded_page_with_total backend\tests\test_workspace_bootstrap.py::test_workspace_bootstrap_bounds_chapter_summaries_for_large_projects -v
```

Expected: FAIL because chapter list/bootstrap do not expose bounded pagination metadata yet.

- [x] **Step 3: Implement backend pagination**

Add `offset`/`limit` query params to `list_chapters`, use count/offset/limit, and apply the same default page in `WorkspaceBootstrapService`.

- [x] **Step 4: Verify GREEN**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_export.py::test_list_chapters_defaults_to_bounded_page_with_total backend\tests\test_export.py::test_list_chapters_returns_explicit_page backend\tests\test_workspace_bootstrap.py::test_workspace_bootstrap_bounds_chapter_summaries_for_large_projects -v
```

Expected: PASS.

## Task 2: Frontend Chapter Metadata

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/stores/project.ts`
- Test: `frontend/src/stores/project.workspace.test.ts`

- [x] **Step 1: Write failing frontend tests**

Update project store tests so `loadChapters` and workspace bootstrap record total/offset/limit/has_more metadata.

- [x] **Step 2: Verify RED**

```powershell
npm --prefix frontend run test:unit -- src/stores/project.workspace.test.ts
```

Expected: FAIL because the store does not expose chapter pagination metadata.

- [x] **Step 3: Implement frontend metadata**

Add typed API response, pagination query params, store refs, reset behavior, and bootstrap/load assignment.

- [x] **Step 4: Verify GREEN**

```powershell
npm --prefix frontend run test:unit -- src/stores/project.workspace.test.ts
```

Expected: PASS.

## Task 3: Verification and Commit

- [x] **Step 1: Focused tests**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_export.py backend\tests\test_workspace_bootstrap.py -v
npm --prefix frontend run test:unit -- src/stores/project.workspace.test.ts
```

- [x] **Step 2: Full verification slice**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests -v
npm --prefix frontend run test:unit
npm --prefix frontend run build
```

- [x] **Step 3: Hygiene checks**

```powershell
git diff --check
rg -n "<exact-sensitive-key>" .
rg -n "sk-[A-Za-z0-9_-]{20,}" .
git status --short
```

- [ ] **Step 4: Commit**

```powershell
git add backend/app/api/export.py backend/app/services/workspace/bootstrap.py backend/app/schemas/workspace.py backend/tests/test_export.py backend/tests/test_workspace_bootstrap.py frontend/src/api/types.ts frontend/src/api/client.ts frontend/src/stores/project.ts frontend/src/stores/project.workspace.test.ts docs/superpowers/plans/2026-05-13-longform-scale-phase13.md
git commit -m "feat: bound chapter summary loading"
```
