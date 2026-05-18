# Phase 202 - Bound Chapter User Feedback

## Problem

Chapter generation gives user feedback the highest prompt priority. Oversized
feedback, such as pasted notes or unrelated draft text, could consume a large
part of the 24k context budget before the chapter target, length constraint,
Athena context, retrieval evidence, style rules, or examples were considered.

The generic trace block limit already capped a single feedback block at 12k
characters, but that is still too large for stable chapter generation and can
leak irrelevant pasted noise into the model prompt.

## Change

- Added a regression test with useful feedback followed by large pasted noise.
- Added a provider-level `EXTRA_FEEDBACK_CHAR_LIMIT` of 3000 characters.
- Chapter prompts now use a compact feedback block plus a Chinese truncation
  notice when feedback is oversized.
- Length constraints are still extracted from the original full feedback, so
  word-count instructions remain available even when the model-facing feedback
  is compacted.

## Tests

- RED: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_prompting_chapter_migration.py::test_chapter_budget_bounds_oversized_user_feedback -q`
  - failed because mid-paste feedback noise was included in the model prompt.
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_prompting_chapter_migration.py::test_chapter_budget_bounds_oversized_user_feedback -q` (`1 passed`)
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_prompting_chapter_migration.py backend\tests\test_chapters.py backend\tests\test_prompting_contracts.py -q` (`62 passed`)
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` (`604 passed`)
- GREEN: `npm run build` from `frontend`
- GREEN: `npm run test:unit` from `frontend` (`407 passed`)
- GREEN: `git diff --check`
- GREEN: DeepSeek key scan returned `NO_MATCH`

## Result

Chapter generation now keeps user intent while preventing oversized feedback
from dominating the prompt budget. This protects the chapter target and length
constraint in long-running writing sessions where users may paste large notes or
draft fragments into a regeneration request.
