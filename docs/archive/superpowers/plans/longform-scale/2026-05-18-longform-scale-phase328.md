# Phase 328: Aggregate Chapter Prose Quality Diagnostics

## Goal

Make outline-like chapter output visible in continuous writing task results, instead of leaving it only inside raw model-call trace metadata.

## Scope

- Read `trace_metadata.chapter_prose_quality` from each generated chapter trace.
- Add `generation_diagnostics.prose_quality` to background task results.
- Count outline-like chapters and keep bounded chapter indexes.
- Add an actionable `outline_like_output` recommendation.

## Verification

- RED confirmed:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py::test_generate_chapter_work_summarizes_generation_diagnostics -q`
  - Failed with missing `generation_diagnostics.prose_quality`.
- GREEN confirmed:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py::test_generate_chapter_work_summarizes_generation_diagnostics -q`
  - `1 passed`
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py -q`
  - `28 passed`

## Follow-Up

- Surface the new prose-quality diagnostic in Hermes so users can see it during long batch writing.
