# Phase149 Recovery Execute Prepare-Only Safety Report

## Objective

Lock down the recovery execution path for resource-binding drift so a confirmed recovery plan can run fresh prepare steps, but cannot silently write a chapter.

## Implementation

- Added an integration regression for a blocked `execute_longform_chapter_batch` run with `resource_binding_target_mismatch`.
- The test confirms:
  - recovery preview returns exactly one `prepare_longform_chapter_batch_execution` tool
  - preview `safe_auto_execute` remains `False`
  - confirmed recovery execution runs only the prepare tool
  - prepare output requires approval before write execution
  - `generate_chapter` is not called
  - chapter 2 content is not written

No production code was required; existing Phase148 recovery policy plus existing recovery execution gates already satisfied the safety invariant.

## Verification

- Targeted test:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_auto_plan_executes_binding_recovery_prepare_only_after_hash_confirmation -q`
  - `1 passed in 0.95s`
- Targeted regression:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_auto_plan_executes_binding_recovery_prepare_only_after_hash_confirmation backend\tests\test_writing_agent_runs.py::test_agent_run_execute_longform_chapter_batch_blocks_resource_binding_mismatch backend\tests\test_writing_agent_runs.py::test_agent_run_can_execute_approved_longform_chapter_batch_once -q`
  - `3 passed in 0.56s`
- Hygiene:
  - `git diff --check` passed.
  - API key scan found no matches in non-archived backend/frontend/docs paths.

## Novel Progress

No new novel chapter was generated. This phase improves long-run safety by proving an Agent recovery step can refresh approval contracts without mutating chapter content.

## Known Limits

- This phase covers longform batch binding recovery execution, not direct single-chapter recovery execution.
- Recovery execution still depends on a fresh `recovery_plan_hash` and explicit confirmation; this phase does not add a UI flow for that confirmation.

## Next Recommendation

Move from recovery safety to Agent planning depth: teach the planner to prefer prepare/recovery flows when a write tool is blocked by binding drift, instead of requiring manual tool selection.
