# Longform Scale Phase 7 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an incremental longform maintenance path so editing or regenerating one chapter refreshes only the affected layered memories and retrieval documents instead of rebuilding the whole thousand-chapter project.

**Architecture:** Keep full rebuild as the authoritative maintenance fallback. Add a targeted memory refresh function in `longform_memory.py` that touches chapter, arc, volume, and global scopes for one chapter, and add a retrieval sync helper in `athena_retrieval.py` for the changed longform memory rows.

**Tech Stack:** Python, SQLAlchemy, existing retrieval index models, pytest.

---

## File Structure

- Modify `backend/app/core/longform_memory.py`: add `refresh_longform_memory_for_chapter` and small helpers for affected range lookup.
- Modify `backend/app/core/athena_retrieval.py`: add `sync_longform_memory_retrieval_documents` for changed memory ids.
- Modify `backend/tests/test_longform_scale.py`: cover incremental memory refresh and changed-memory retrieval sync.
- Update this plan as tasks are executed.

## Success Criteria

- Editing chapter 45 in a 120-chapter project refreshes only `chapter:45`, `arc:41-60`, `volume:1-100`, and `global`.
- Unrelated memory ids such as `chapter:44` remain unchanged.
- Memory counts remain `{"chapter": 120, "arc": 6, "volume": 2, "global": 1}` after refresh.
- Project current word count is reconciled after a single-chapter word count change.
- Retrieval sync updates only the changed longform memory documents and leaves unrelated memory retrieval documents untouched.
- On a temporary 1000-chapter smoke project, editing chapter 500 refreshes and syncs 4 affected scopes in a bounded incremental pass.
- Focused tests, backend tests, diff hygiene, and sensitive-key scan pass before commit.

## Task 1: Incremental Memory Refresh

**Files:**
- Modify: `backend/app/core/longform_memory.py`
- Modify: `backend/tests/test_longform_scale.py`

- [x] **Step 1: Write failing test**

Add `test_refresh_longform_memory_for_chapter_updates_only_affected_scopes`:

- Seed 120 generated chapters.
- Run `rebuild_longform_memory`.
- Capture ids for `chapter:44`, `chapter:45`, `arc:41-60`, `volume:1-100`, and `global`.
- Edit chapter 45 content and `word_count`.
- Call `refresh_longform_memory_for_chapter(db_session, project.id, 45)`.
- Assert updated scopes are exactly `["arc:41-60", "chapter:45", "global", "volume:1-100"]`.
- Assert `chapter:44` id is unchanged, affected ids changed, counts are unchanged, and project word count reflects the edit.

- [x] **Step 2: Verify RED**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_refresh_longform_memory_for_chapter_updates_only_affected_scopes -v
```

Expected: FAIL because `refresh_longform_memory_for_chapter` does not exist.

- [x] **Step 3: Implement memory refresh**

Implementation requirements:

- Validate project and chapter existence.
- Compute affected arc and volume ranges using existing `DEFAULT_ARC_SIZE` and `DEFAULT_VOLUME_SIZE`.
- Delete only overlapping affected memory rows for the chapter, arc, volume, and global scopes.
- Recreate the chapter memory, affected arc memory, affected volume memory, and global memory.
- Reconcile project word count.
- Return `updated_scope_keys`, `updated_memory_ids`, `counts_by_type`, and `current_word_count`.

- [x] **Step 4: Verify GREEN**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_refresh_longform_memory_for_chapter_updates_only_affected_scopes -v
```

Expected: PASS.

## Task 2: Incremental Longform Retrieval Sync

**Files:**
- Modify: `backend/app/core/athena_retrieval.py`
- Modify: `backend/tests/test_longform_scale.py`

- [x] **Step 1: Write failing test**

Add `test_sync_changed_longform_memory_retrieval_documents_preserves_unrelated_docs`:

- Seed 80 chapters, rebuild memory, and run `reindex_project_retrieval`.
- Capture retrieval document ids for `memory:chapter:44` and `memory:chapter:45`.
- Edit chapter 45 with a unique phrase near the start, refresh memory for chapter 45, then call `sync_longform_memory_retrieval_documents` with the returned memory ids.
- Assert the `memory:chapter:44` retrieval document id is unchanged.
- Assert the `memory:chapter:45` retrieval document id changes and search for the unique phrase returns a `longform_memory` hit.

- [x] **Step 2: Verify RED**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_sync_changed_longform_memory_retrieval_documents_preserves_unrelated_docs -v
```

Expected: FAIL because `sync_longform_memory_retrieval_documents` does not exist.

- [x] **Step 3: Implement retrieval sync**

Implementation requirements:

- Load changed `LongformMemory` rows by id.
- For each memory, delete any existing retrieval document by stable `source_ref == f"memory:{scope_key}"`.
- Reindex only the changed memory rows by reusing `_longform_memory_source` and `_index_sources`.
- Commit once and return indexed counts plus synced scope keys.

- [x] **Step 4: Verify GREEN**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_sync_changed_longform_memory_retrieval_documents_preserves_unrelated_docs -v
```

Expected: PASS.

## Task 3: Verification and Commit

- [x] **Step 1: Run focused longform tests**

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
git add backend/app/core/longform_memory.py backend/app/core/athena_retrieval.py backend/tests/test_longform_scale.py docs/superpowers/plans/2026-05-13-longform-scale-phase7.md
git commit -m "feat: add incremental longform maintenance"
```
