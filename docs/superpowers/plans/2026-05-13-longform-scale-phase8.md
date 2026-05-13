# Longform Scale Phase 8 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire incremental longform maintenance into real chapter write paths so generated and regenerated chapters automatically refresh layered memory and longform retrieval documents.

**Architecture:** Keep generation success independent from maintenance success. Add a safe helper in `backend/app/api/chapters.py` that calls `refresh_longform_memory_for_chapter` and `sync_longform_memory_retrieval_documents`, swallows maintenance errors like existing Athena/retrieval side effects, and reuse it from `create_or_replace_chapter`, which revision regeneration already calls.

**Tech Stack:** FastAPI chapter APIs, SQLAlchemy, existing longform memory/retrieval helpers, pytest.

---

## File Structure

- Modify `backend/app/api/chapters.py`: add `_safe_refresh_longform_maintenance` and call it after chapter content is committed.
- Modify `backend/tests/test_chapters.py`: prove normal chapter generation updates affected longform memory and longform retrieval docs.
- Modify `backend/tests/test_chapter_revisions.py`: prove revision regeneration uses the same maintenance path.
- Update this plan as tasks are executed.

## Success Criteria

- Generating an existing chapter in a project with longform memory updates the changed chapter memory and related retrieval document.
- Unrelated longform memory retrieval documents keep their ids.
- Revision regeneration updates longform memory and retrieval because it goes through `create_or_replace_chapter`.
- Maintenance failures do not fail chapter generation.
- Focused tests, backend tests, diff hygiene, and sensitive-key scan pass before commit.

## Task 1: Chapter Generation Maintenance

**Files:**
- Modify: `backend/app/api/chapters.py`
- Modify: `backend/tests/test_chapters.py`

- [ ] **Step 1: Write failing test**

Add `test_generate_chapter_refreshes_longform_memory_and_retrieval`:

- Create project and setup.
- Seed chapters 1-3.
- Run `rebuild_longform_memory` and `reindex_project_retrieval`.
- Capture `memory:chapter:1` and `memory:chapter:2` retrieval document ids.
- Generate chapter 2 with unique content.
- Assert `chapter:2` memory summary contains the unique phrase.
- Assert `memory:chapter:1` retrieval document id is unchanged.
- Assert `memory:chapter:2` retrieval document id changed.
- Assert `search_retrieval(..., source_type="longform_memory")` returns a `memory:chapter:2` hit for the unique phrase.

- [ ] **Step 2: Verify RED**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py::test_generate_chapter_refreshes_longform_memory_and_retrieval -v
```

Expected: FAIL because generation currently indexes chapter content only and does not refresh longform memory/retrieval.

- [ ] **Step 3: Implement safe maintenance helper**

Implementation requirements:

- Add `_safe_refresh_longform_maintenance(db, project_id, chapter_index)`.
- Inside it, call `refresh_longform_memory_for_chapter`, then `sync_longform_memory_retrieval_documents` with returned ids.
- Catch exceptions and roll back without failing generation.
- Call helper after the main chapter commit and before returning from `create_or_replace_chapter`.

- [ ] **Step 4: Verify GREEN**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py::test_generate_chapter_refreshes_longform_memory_and_retrieval -v
```

Expected: PASS.

## Task 2: Revision Regeneration Maintenance

**Files:**
- Modify: `backend/tests/test_chapter_revisions.py`

- [ ] **Step 1: Write test**

Add `test_regenerate_revision_refreshes_longform_memory_and_retrieval`:

- Create project, setup, and chapter 1.
- Run `rebuild_longform_memory` and `reindex_project_retrieval`.
- Submit a revision for chapter 1.
- Regenerate with unique content.
- Assert `chapter:1` memory summary contains the unique phrase.
- Assert searching longform memory returns a `memory:chapter:1` hit.

- [ ] **Step 2: Run focused test**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapter_revisions.py::test_regenerate_revision_refreshes_longform_memory_and_retrieval -v
```

Expected: PASS once Task 1 implementation is present.

## Task 3: Maintenance Failure Isolation

**Files:**
- Modify: `backend/tests/test_chapters.py`

- [ ] **Step 1: Write test**

Add `test_generate_chapter_does_not_fail_when_longform_maintenance_fails`:

- Patch `app.api.chapters.refresh_longform_memory_for_chapter` to raise.
- Generate a chapter.
- Assert response status is 200 and content is saved.

- [ ] **Step 2: Run focused test**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py::test_generate_chapter_does_not_fail_when_longform_maintenance_fails -v
```

Expected: PASS after helper catches maintenance exceptions.

## Task 4: Verification and Commit

- [ ] **Step 1: Run focused tests**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py::test_generate_chapter_refreshes_longform_memory_and_retrieval backend\tests\test_chapters.py::test_generate_chapter_does_not_fail_when_longform_maintenance_fails backend\tests\test_chapter_revisions.py::test_regenerate_revision_refreshes_longform_memory_and_retrieval -v
```

- [ ] **Step 2: Run backend tests**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests -v
```

- [ ] **Step 3: Hygiene checks**

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9_-]{20,}" backend docs frontend scripts
git status --short
```

Expected: diff check passes, exact sensitive-key scan returns no matches, and broad secret-pattern matches are limited to sanitizer test fixtures.

- [ ] **Step 4: Commit**

```powershell
git add backend/app/api/chapters.py backend/tests/test_chapters.py backend/tests/test_chapter_revisions.py docs/superpowers/plans/2026-05-13-longform-scale-phase8.md
git commit -m "feat: maintain longform memory after chapter writes"
```
