# Longform Scale Phase 9 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add visible longform maintenance diagnostics so thousand-chapter projects can detect stale chapter memories and stale longform-memory retrieval documents after edits or failed maintenance.

**Architecture:** Do not rebuild or mutate data in diagnostics. Compare generated chapter rows, chapter-scope `LongformMemory` rows, and `RetrievalDocument` rows for `source_type=longform_memory` to report missing/stale coverage and the latest synced chapter.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic schemas, pytest.

---

## File Structure

- Modify `backend/app/core/longform_memory.py`: add `get_longform_maintenance_diagnostics`.
- Modify `backend/app/schemas/longform_memory.py`: add response schemas.
- Modify `backend/app/api/athena_longform.py`: add `GET /longform/maintenance/diagnostics`.
- Modify `backend/tests/test_longform_scale.py`: cover stale memory and stale retrieval detection.
- Update this plan as tasks are executed.

## Success Criteria

- Diagnostics reports `status=current` when generated chapters, chapter memories, and longform memory retrieval documents are aligned.
- Diagnostics reports stale chapter memory when a chapter was edited after its `chapter:N` memory was built.
- Diagnostics reports stale retrieval when a longform memory was refreshed after its `memory:chapter:N` retrieval document was indexed.
- Diagnostics includes bounded `stale_chapter_indexes`, `stale_retrieval_chapter_indexes`, `missing_memory_chapter_indexes`, `missing_retrieval_chapter_indexes`, and `latest_synced_chapter_index`.
- API response validates through Pydantic.
- Focused tests, backend tests, diff hygiene, and sensitive-key scan pass before commit.

## Task 1: Stale Chapter Memory Diagnostics

**Files:**
- Modify: `backend/app/core/longform_memory.py`
- Modify: `backend/app/schemas/longform_memory.py`
- Modify: `backend/app/api/athena_longform.py`
- Modify: `backend/tests/test_longform_scale.py`

- [x] **Step 1: Write failing API test**

Add `test_longform_maintenance_diagnostics_reports_stale_memory_after_chapter_edit`:

- Create project with 3 generated chapters.
- Run `rebuild_longform_memory`.
- Edit chapter 2 content and commit.
- Call `GET /api/v1/projects/{project_id}/athena/longform/maintenance/diagnostics`.
- Assert `status == "stale"`, `stale_chapter_indexes == [2]`, `stale_memory_count == 1`, and `chapter_count == 3`.

- [x] **Step 2: Verify RED**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_maintenance_diagnostics_reports_stale_memory_after_chapter_edit -v
```

Expected: FAIL because the endpoint does not exist.

- [x] **Step 3: Implement memory diagnostics**

Implementation requirements:

- Use generated/content-bearing chapters ordered by `chapter_index`.
- Build `chapter:N` memory lookup.
- Mark missing memory and stale memory separately.
- Return bounded lists with default limit 20.
- Compute `status` as `stale` if any missing/stale count is non-zero.

- [x] **Step 4: Verify GREEN**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_maintenance_diagnostics_reports_stale_memory_after_chapter_edit -v
```

Expected: PASS.

## Task 2: Stale Retrieval Diagnostics

**Files:**
- Modify: `backend/app/core/longform_memory.py`
- Modify: `backend/tests/test_longform_scale.py`

- [x] **Step 1: Write failing test**

Add `test_longform_maintenance_diagnostics_reports_stale_retrieval_after_memory_refresh`:

- Create project with 3 generated chapters.
- Run `rebuild_longform_memory` and `reindex_project_retrieval`.
- Edit chapter 2 and run `refresh_longform_memory_for_chapter` without retrieval sync.
- Call diagnostics.
- Assert `status == "stale"`, `stale_retrieval_chapter_indexes == [2]`, `stale_retrieval_count == 1`, and `latest_synced_chapter_index == 3`.

- [x] **Step 2: Verify RED**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_maintenance_diagnostics_reports_stale_retrieval_after_memory_refresh -v
```

Expected: FAIL because retrieval staleness is not reported yet.

- [x] **Step 3: Implement retrieval diagnostics**

Implementation requirements:

- Build retrieval document lookup by `source_ref == memory:chapter:N`.
- Mark missing retrieval and stale retrieval separately.
- Include `latest_synced_chapter_index` from available chapter-memory retrieval docs.
- Keep diagnostics read-only.

- [x] **Step 4: Verify GREEN**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_maintenance_diagnostics_reports_stale_retrieval_after_memory_refresh -v
```

Expected: PASS.

## Task 3: Verification and Commit

- [x] **Step 1: Run focused tests**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py -v
```

- [x] **Step 2: Run backend tests**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests -v
```

- [x] **Step 3: Hygiene checks**

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9_-]{20,}" backend docs frontend scripts
git status --short
```

Expected: diff check passes, exact sensitive-key scan returns no matches, broad secret-pattern matches are limited to sanitizer test fixtures.

- [x] **Step 4: Commit**

```powershell
git add backend/app/core/longform_memory.py backend/app/schemas/longform_memory.py backend/app/api/athena_longform.py backend/tests/test_longform_scale.py docs/superpowers/plans/2026-05-13-longform-scale-phase9.md
git commit -m "feat: expose longform maintenance diagnostics"
```
