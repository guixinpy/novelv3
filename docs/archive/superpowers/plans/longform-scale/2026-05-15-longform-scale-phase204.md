# Phase 204 - Bound Storyline Setup Prompt

## Problem

Storyline generation injected full Setup JSON into template variables:

- `world_building`
- `characters`
- `core_concept`

Unlike chapter generation, this path did not go through a prompt budgeter. A
large Setup draft could therefore expand the actual model prompt directly. The
same helper also feeds outline generation setup variables, so this risk affected
early longform planning beyond the storyline endpoint.

## Change

- Added a regression test that builds the storyline call payload directly with
  oversized Setup fields.
- Added bounded Setup JSON formatting in `build_setup_context_values`.
- Applied budgets:
  - world-building: 2000 characters.
  - characters: 2000 characters.
  - core concept: 1200 characters.
- Short Setup JSON remains unchanged.

## Tests

- RED: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_storylines.py::test_storyline_prompt_bounds_oversized_setup_context -q`
  - failed because the old storyline prompt included mid-block Setup noise.
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_storylines.py::test_storyline_prompt_bounds_oversized_setup_context -q` (`1 passed`)
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_storylines.py backend\tests\test_outlines.py backend\tests\test_prompting_generation_migration.py -q` (`17 passed`)
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` (`606 passed`)
- GREEN: `npm run build` from `frontend`
- GREEN: `npm run test:unit` from `frontend` (`407 passed`)
- GREEN: `git diff --check`
- GREEN: DeepSeek key scan returned `NO_MATCH`

## Result

Storyline and outline generation now receive bounded Setup context before the
template is rendered. This protects early longform planning from oversized Setup
drafts while keeping key anchors available to the model.
