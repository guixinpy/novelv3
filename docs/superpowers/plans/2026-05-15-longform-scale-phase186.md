# Phase 186 - Stream Outline Chapters During Export

## Problem

Chapter body export already streamed chapter rows, but outline export still
loaded the full `Outline.chapters` JSON column through the ORM before writing the
file. On thousand-chapter projects this makes export hold a large outline JSON
blob in memory even though the output can be emitted chapter by chapter.

## Change

- Added a regression test that exports a 1000-chapter outline and captures SQL.
- Replaced ORM outline loading with `json_each(outlines.chapters)` iteration.
- Emit the outline heading only after the first streamed outline chapter exists.
- Kept Markdown/TXT export behavior and chapter body streaming unchanged.

## Tests

- RED: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_export.py::test_export_outline_does_not_select_full_chapter_json -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_export.py::test_export_outline_does_not_select_full_chapter_json -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_export.py -q` (`11 passed`)
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` (`592 passed`)
- GREEN: `npm run test:unit` from `frontend` (`402 passed`)
- GREEN: `npm run build` from `frontend`
- GREEN: `git diff --check`
- GREEN: DeepSeek key scan returned `NO_MATCH`

## Result

Project export no longer selects the full outline chapter JSON column when
writing outline content. Large outline exports now use the same bounded-memory
pattern as chapter body export.
