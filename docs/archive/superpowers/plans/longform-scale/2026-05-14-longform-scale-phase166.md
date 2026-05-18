# Phase 166 - Refresh chapter retrieval after version edits

## Goal

Keep chapter-body retrieval current when a chapter is edited through the version system.

## Why

Version save and rollback can overwrite `ChapterContent.content`. The longform memory refresh already updated memory retrieval, but the direct chapter retrieval document stayed stale. In long novels this can make the next chapter's query-aware retrieval pull old facts from the edited chapter.

## TDD

RED:

- Extended the chapter version apply test to search `source_type=chapter` after saving edited chapter content.
- It failed because only the `longform_memory` document contained the new phrase.

GREEN:

- The version maintenance refresh now indexes the changed chapter retrieval document before refreshing longform memory.
- Chapter retrieval failure remains isolated and does not block the memory refresh attempt.

## Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_versions.py::test_chapter_version_apply_refreshes_longform_memory_and_retrieval -q` -> 1 passed
