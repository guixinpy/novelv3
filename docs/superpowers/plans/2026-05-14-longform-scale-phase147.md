# Phase 147 - Incremental chapter word count update

## Goal

Avoid full-project `SUM(chapter.word_count)` scans during chapter generation and replacement.

## Why

Long web novels are generated one chapter at a time. Recomputing total words from all chapters on every generated chapter creates cumulative scan cost as the project grows.

## TDD

RED:

- Tightened chapter generation tests to assert the generation path does not issue `SUM(chapter_contents.word_count)`.
- Added replacement coverage so overwriting an existing chapter subtracts the old word count and adds the new one.
- Both tests failed because chapter save and follow-up longform maintenance recomputed aggregate word count.

GREEN:

- Chapter save now updates `Project.current_word_count` by delta.
- The generation-triggered single-chapter longform memory refresh now reuses the already-updated project word count.
- Standalone longform memory refresh keeps the default reconciliation behavior for repair/diagnostic paths.

## Verification

- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py::test_generate_chapter_updates_project_word_count_incrementally backend\tests\test_chapters.py::test_replace_chapter_updates_project_word_count_incrementally -q` -> 2 passed
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py backend\tests\test_longform_scale.py -q` -> 63 passed
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests -q` -> 570 passed
- `.\backend\.venv\Scripts\python.exe scripts\longform_scale_smoke.py --chapters 1000 --words-per-chapter 1000 --cleanup` -> passed, retrieval reindex 8,611 ms, elapsed 9,377 ms
- `git diff --check` -> passed
- Exact DeepSeek key scan -> no matches
