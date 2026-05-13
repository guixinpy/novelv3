# Longform Scale Phase 23 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent single-chapter longform memory refresh from selecting every chapter's content.

**Architecture:** Keep `refresh_longform_memory_for_chapter` behavior stable while changing its chapter reads from full-project content scans to targeted queries. The target chapter may select content for its own chapter memory; arc and volume memories only need chapter titles and word counts; global memory only needs aggregate count, word count, and first/latest chapter indexes.

**Tech Stack:** SQLAlchemy, Pytest.

---

### Task 1: Targeted Refresh Queries

**Files:**
- Modify: `backend/app/core/longform_memory.py`
- Test: `backend/tests/test_longform_scale.py`

- [x] **Step 1: Write failing SQL projection test**

Add a test that captures SQL during `refresh_longform_memory_for_chapter` after a full memory rebuild. Assert refresh still updates `chapter`, `arc`, `volume`, and `global` memories, but only one `chapter_contents` SELECT clause includes `chapter_contents.content`, and no chapter SELECT includes generation metadata columns.

- [x] **Step 2: Run test to verify failure**

Run:
- `cd backend; .\.venv\Scripts\python.exe -m pytest tests/test_longform_scale.py::test_refresh_longform_memory_for_chapter_avoids_full_content_scan -q`

Expected: FAIL because current refresh selects target chapter content and then selects content for all chapters through `_chapters`.

- [x] **Step 3: Implement targeted refresh reads**

In `backend/app/core/longform_memory.py`:
- Add `_chapter_for_memory` selecting `chapter_index`, `title`, `content`, `word_count`, and `status` for the target chapter.
- Add `_range_chapters` selecting `chapter_index`, `title`, and `word_count` for the affected arc or volume range.
- Add `_global_memory_from_stats` using aggregate count, sum, min chapter index, and max chapter index.
- Update `refresh_longform_memory_for_chapter` to use those helpers instead of `_chapters` and `_chapter_range`.

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

Commit message: `perf: target longform memory refresh reads`
