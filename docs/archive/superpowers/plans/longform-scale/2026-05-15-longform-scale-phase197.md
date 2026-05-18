# Phase 197 - Bound Outline Storyline Prompt Context

## Problem

Generating an outline loaded the full `Storyline.plotlines` and
`Storyline.foreshadowing` JSON arrays, then embedded them directly into the
outline prompt and model-call trace. For long-form projects, this could drag
large milestone trees and hundreds of foreshadowing entries into one generation
request before the outline itself is produced.

## Change

- Added a regression test with 60 storylines, 500 foreshadowing entries, and
  1000 milestones per storyline.
- Added a bounded storyline-context query for outline generation:
  - storylines: total count plus the first 20 summaries.
  - foreshadowing: total count plus the first 100 summaries.
  - milestones: count only, without expanding full milestone arrays.
- Switched outline generation to pass the bounded context string into the prompt
  and trace blocks.
- Kept existing prompt-provider behavior compatible with legacy callers that
  still pass a `Storyline` model instance.
- Verified SQL no longer selects `Storyline.plotlines` or
  `Storyline.foreshadowing` as full ORM JSON columns for this generation path.

## Tests

- RED: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_outlines.py::test_generate_outline_uses_bounded_storyline_context_without_selecting_full_json -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_outlines.py::test_generate_outline_uses_bounded_storyline_context_without_selecting_full_json -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_outlines.py backend\tests\test_prompting_generation_migration.py backend\tests\test_prompting_static_quality.py -q` (`26 passed`)
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` (`601 passed`)
- GREEN: `npm run build` from `frontend`
- GREEN: `npm run test:unit` from `frontend` (`407 passed`)
- GREEN: `git diff --check`
- GREEN: DeepSeek key scan returned `NO_MATCH`

## Result

Outline generation now uses bounded storyline context instead of serializing the
full story graph. This lowers prompt bloat and memory pressure in the path that
turns early narrative planning into chapter-scale outlines.
