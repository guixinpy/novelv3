# Phase 196 - Patch Outline Chapters In Place

## Problem

Updating one outline chapter loaded the full `Outline.chapters` JSON array into
Python, modified one item, and wrote the whole array back. For a thousand-chapter
plan, ordinary outline edits caused avoidable large JSON reads and rewrites.

## Change

- Added a regression test around patching chapter 512 in a 1000-chapter outline.
- Changed `update_chapter_outline()` to select only the outline id first.
- Used `json_each(outlines.chapters)` to locate the matching chapter array key.
- Used SQLite `json_set()` to update only supplied fields at the matched JSON
  path.
- Preserved existing behavior:
  - `404` when outline is missing.
  - `404` when the chapter is not in the outline.
  - unspecified fields remain unchanged.
  - empty patch still succeeds if the chapter exists.

## Tests

- RED: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_outlines.py::test_patch_outline_chapter_updates_json_without_selecting_full_chapters -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_outlines.py::test_patch_outline_chapter_updates_json_without_selecting_full_chapters -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_outlines.py backend\tests\test_final_gaps.py backend\tests\test_athena_evolution_plan.py -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` (`600 passed`)
- GREEN: `npm run build` from `frontend`
- GREEN: `npm run test:unit` from `frontend` (`407 passed`)
- GREEN: `git diff --check`
- GREEN: DeepSeek key scan returned `NO_MATCH`

## Result

Single-chapter outline edits now avoid selecting the full chapter array and use a
targeted JSON update. This makes frequent plan grooming safer for thousand-
chapter projects.
