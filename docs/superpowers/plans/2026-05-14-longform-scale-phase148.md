# Phase 148 - Dialog context word count projection

## Goal

Avoid full chapter word-count aggregation while building Athena/Hermes dialog context.

## Why

Longform chat is a frequent workflow. Context blocks should not recompute total manuscript words from every chapter when `Project.current_word_count` is already maintained by chapter generation, project detail reconciliation, and longform rebuild/repair paths.

## TDD

RED:

- Extended the Athena manuscript context SQL-capture test to reject `SUM(chapter_contents.word_count)`.
- Extended the longform evidence-range SQL-capture test to reject the same aggregate and assert it uses the project word count.
- Both tests failed because dialog context rebuilt total words from chapter rows.

GREEN:

- Athena manuscript context now queries only chapter count and chapter range.
- Longform evidence-range context now uses `Project.current_word_count` directly.

## Verification

- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_athena_dialog.py::test_athena_manuscript_context_uses_limited_chapter_summary_queries -q` -> 1 passed
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_evidence_range_chapter_count_does_not_select_chapter_content -q` -> 1 passed
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_athena_dialog.py backend\tests\test_longform_scale.py -q` -> 58 passed
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests -q` -> 570 passed
- `.\backend\.venv\Scripts\python.exe scripts\longform_scale_smoke.py --chapters 1000 --words-per-chapter 1000 --cleanup` -> passed, retrieval reindex 8,855 ms, elapsed 9,617 ms
- `git diff --check` -> passed
- Exact DeepSeek key scan -> no matches
