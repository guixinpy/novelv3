# Phase 327: Chapter Prose Quality Trace Warning

## Goal

Strengthen longform generation observability by recording when a generated chapter looks like an outline or summary instead of continuous prose.

## Scope

- Add a chapter generation trace metadata field: `chapter_prose_quality`.
- Detect outline-like output with lightweight structural signals:
  - multiple non-empty lines;
  - repeated outline markers such as chapter, scene, role, summary, objective, conflict, foreshadowing, ending, bullets, or numbered items;
  - low sentence-ending density.
- Keep the generated chapter saved successfully. This phase records a warning only; it does not reject model output.

## Verification

- RED confirmed:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py::test_generate_chapter_records_outline_like_quality_warning -q`
  - Failed with missing `chapter_prose_quality`.
- GREEN confirmed:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py::test_generate_chapter_records_outline_like_quality_warning -q`
  - `1 passed`
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py -q`
  - `37 passed`

## Follow-Up

- Aggregate `chapter_prose_quality` warnings into writing diagnostics so Hermes can surface them without opening raw model-call traces.
