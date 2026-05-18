# Phase 143 - Reject empty generated chapters

## Goal

Prevent chapter generation from saving empty or title-only model output after markdown fence and heading normalization.

## Why

For long-form writing, a single blank saved chapter can poison downstream memory, retrieval, world-model analysis, export, and retry decisions. The generation path should fail loudly and keep the previous state intact when the model returns unusable text.

## TDD

RED:

- `test_generate_chapter_rejects_empty_content_after_normalization` used a fenced response containing only a chapter heading.
- It failed because the endpoint returned `200` and saved the heading as chapter content.

GREEN:

- Heading normalization now removes a chapter heading even when it is the only line.
- Added an empty-content quality gate after normalization.
- Empty generated content marks the model call trace as `failed`, returns `502`, and does not create a chapter row.

## Verification

- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py::test_generate_chapter_rejects_empty_content_after_normalization backend\tests\test_chapters.py::test_generate_chapter_strips_markdown_fence_and_heading_before_saving -q`
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py -q`
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py -q`
