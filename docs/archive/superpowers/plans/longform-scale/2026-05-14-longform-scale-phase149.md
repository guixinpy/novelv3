# Phase 149 - Version apply word count delta

## Goal

Keep project word-count statistics stable and cheap when applying chapter versions.

## Why

Version apply and rollback are long-running novel maintenance workflows. A single chapter edit should not trigger full-book word-count aggregation in a 1,000+ chapter project when the old and new chapter counts are already known.

## TDD

RED:

- Added a version-apply SQL-capture test that seeds two chapters and a maintained project word count.
- The test asserts the edited chapter count changes from 12 to 13, the project count changes from 30 to 31, and the request does not run `SUM(chapter_contents.word_count)`.
- The test failed because the post-apply longform refresh reconciled total words by aggregating all chapter rows.

GREEN:

- Chapter version application now updates `Project.current_word_count` by delta.
- The follow-up single-chapter longform refresh reuses the maintained project word count instead of reconciling through a full aggregate.

## Verification

- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_versions.py::test_chapter_version_apply_updates_project_word_count_incrementally -q` -> 1 passed
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_versions.py -q` -> 8 passed
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests -q` -> 571 passed
- `.\backend\.venv\Scripts\python.exe scripts\longform_scale_smoke.py --chapters 1000 --words-per-chapter 1000 --cleanup` -> passed, retrieval reindex 10,262 ms, elapsed 11,120 ms
- `git diff --check` -> passed
- Exact DeepSeek key scan -> no matches
