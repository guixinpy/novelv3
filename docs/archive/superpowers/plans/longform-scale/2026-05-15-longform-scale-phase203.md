# Phase 203 - Bound Chapter Setup Blocks

## Problem

Chapter generation still injected Setup world-building, character, and core
concept JSON directly into prompt context blocks. The global prompt budget could
truncate or omit blocks later, but each Setup block could still contribute up to
the generic trace block limit and carry irrelevant import/paste noise into model
prompts.

In large projects this also made one oversized world-building block capable of
crowding out the character Setup block.

## Change

- Added a regression test with useful Setup anchors plus large mid-block noise.
- Added provider-level Setup block budgets:
  - world-building: 2000 characters.
  - characters: 2000 characters.
  - core concept: 1200 characters.
- Added Chinese truncation notices for oversized Setup blocks.
- Kept normal short Setup JSON unchanged.

## Tests

- RED: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_prompting_chapter_migration.py::test_chapter_budget_bounds_oversized_setup_blocks -q`
  - failed because the old prompt lost the character anchor and included trace truncation noise.
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_prompting_chapter_migration.py::test_chapter_budget_bounds_oversized_setup_blocks -q` (`1 passed`)
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_prompting_chapter_migration.py backend\tests\test_chapters.py backend\tests\test_prompting_contracts.py -q` (`63 passed`)
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` (`605 passed`)
- GREEN: `npm run build` from `frontend`
- GREEN: `npm run test:unit` from `frontend` (`407 passed`)
- GREEN: `git diff --check`
- GREEN: DeepSeek key scan returned `NO_MATCH`

## Result

Chapter generation now receives compact Setup context that preserves key anchors
while avoiding raw large JSON blocks. This is especially important before a
project has fully migrated its Setup draft into the canonical world model.
