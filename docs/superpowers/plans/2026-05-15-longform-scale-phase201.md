# Phase 201 - Bound World-Model Prompt Values

## Problem

After a project has a formal world-model profile, several prompt assembly paths
still formatted full JSON or long text values directly into Athena, Hermes, and
chapter-generation context:

- `WorldRule.statement`
- `WorldFactClaim.object_ref_or_value`
- `WorldEvent.primitive_payload`

For a million-word project, these fields can accumulate extracted evidence,
long summaries, or imported payloads. Sending the complete values into every
prompt increases token cost and makes long-running writing sessions less stable.

## Change

- Added a regression test with oversized rule, fact, and event values.
- Introduced bounded context formatting for prompt-facing world-model values.
- Applied the budgeted formatting to:
  - Athena world-rule blocks.
  - Athena and Hermes world-fact blocks.
  - Athena timeline-event blocks.
  - Chapter context rules and confirmed facts.
- Short values keep their existing formatting, preserving existing behavior for
  normal projects.

## Tests

- RED: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_athena_dialog.py::test_world_context_bounds_large_world_model_values -q`
  - failed because the old context included the long fact/event tails.
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_athena_dialog.py::test_world_context_bounds_large_world_model_values -q` (`1 passed`)
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_athena_dialog.py backend\tests\test_prompting_dialog_migration.py -q` (`28 passed`)
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` (`603 passed`)
- GREEN: `npm run build` from `frontend`
- GREEN: `npm run test:unit` from `frontend` (`407 passed`)
- GREEN: `git diff --check`
- GREEN: DeepSeek key scan returned `NO_MATCH`

## Result

World-model prompts now carry bounded rule, fact, and event values. This reduces
the risk that a few large canonical records dominate Athena or Hermes prompts as
the project grows toward thousand-chapter scale.
