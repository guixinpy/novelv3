# Phase 205 - Bound Generation Command Args

## Problem

Setup, storyline, and outline generation share `build_generation_payload`, which
appended `command_args` directly to the model prompt as `附加要求`. The trace
context block for command args also stored the raw text through the generic
trace limit.

Large pasted command arguments could therefore inject irrelevant noise into
generation prompts and traces.

## Change

- Added a regression test covering both model-message command args and the trace
  command-args block.
- Added a shared `compact_command_args` helper with a 3000-character budget.
- Applied it to:
  - `build_generation_payload` prompt suffixes.
  - `build_command_args_block` trace context blocks.
- Short command args remain unchanged.

## Tests

- RED: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_prompting_contracts.py::test_build_generation_payload_bounds_oversized_command_args -q`
  - failed because mid-block command-args noise was included.
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_prompting_contracts.py::test_build_generation_payload_bounds_oversized_command_args -q` (`1 passed`)
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_prompting_contracts.py backend\tests\test_setups.py backend\tests\test_storylines.py backend\tests\test_outlines.py -q` (`47 passed`)
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` (`607 passed`)
- GREEN: `npm run build` from `frontend`
- GREEN: `npm run test:unit` from `frontend` (`407 passed`)
- GREEN: `git diff --check`
- GREEN: DeepSeek key scan returned `NO_MATCH`

## Result

Generation commands now preserve concise user intent while preventing large
pasted command arguments from dominating prompts or traces.
