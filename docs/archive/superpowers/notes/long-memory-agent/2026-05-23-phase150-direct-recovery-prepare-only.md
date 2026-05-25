# Phase150 Direct Recovery Prepare-Only Safety Report

## Objective

Extend recovery execution safety coverage to direct single-chapter generation, proving a binding-drift recovery can refresh approval state without generating chapter content.

## Implementation

- Added an integration regression for a blocked `execute_generate_chapter_with_approval` run with `resource_binding_target_mismatch`.
- The test confirms:
  - recovery preview returns exactly one `prepare_generate_chapter_execution` tool
  - preview `safe_auto_execute` remains `False`
  - confirmed recovery execution runs only the prepare tool
  - prepare output returns `approval_required`
  - `generate_chapter` is not called
  - chapter 2 content is not written

No production code was required. Existing recovery execution gates and Phase148 recovery policy already satisfy this direct path invariant.

## Verification

- Targeted test:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_auto_plan_executes_direct_binding_recovery_prepare_only_after_hash_confirmation -q`
  - `1 passed in 0.87s`
- Targeted regression:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_auto_plan_executes_direct_binding_recovery_prepare_only_after_hash_confirmation backend\tests\test_writing_agent_runs.py::test_agent_run_auto_plan_executes_binding_recovery_prepare_only_after_hash_confirmation backend\tests\test_writing_agent_chapter_generation_execution.py::test_execute_generate_chapter_with_approval_blocks_resource_binding_mismatch -q`
  - `3 passed in 0.40s`
- Hygiene:
  - `git diff --check` passed.
  - API key scan found no matches in non-archived backend/frontend/docs paths.

## Novel Progress

No new novel chapter was generated. This phase strengthens the Agent write gate by ensuring direct chapter recovery stays approval-refresh-only.

## Known Limits

- The test covers direct binding mismatch recovery execution. Missing-binding execution likely follows the same policy path, but is not separately exercised at the run-service level.
- The Agent still needs planner-level improvements so users do not have to manually know when to inspect or execute recovery previews.

## Next Recommendation

Improve planner behavior around blocked runs: when the user asks to continue or recover after a blocked Agent run, the planner should route to `plan_recovery_tools` and explain whether the next action is preview-only or confirmation-gated execution.
