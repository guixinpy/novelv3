# Phase148 Binding Recovery Policy Report

## Objective

Route resource binding drift in blocked write tools back to fresh prepare steps, so the Writing Agent can recover from stale or mismatched approval bindings without bypassing approval.

## Implementation

- Added binding recovery policy for:
  - `execute_longform_chapter_batch`
  - `execute_generate_chapter_with_approval`
- Covered both binding failure reasons:
  - `resource_binding_target_mismatch`
  - `resource_binding_missing`
- Exposed `next_params` in continuation recovery summaries so the Agent can show the exact prepare command to run.
- Kept execution guards unchanged. Recovery points only to prepare tools, not write execution tools.
- Added recovery preview safety coverage:
  - preview tool list contains only the prepare tool
  - `safe_auto_execute` remains `False`

## TDD Evidence

- Batch mismatch RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_execute_longform_chapter_batch_blocks_resource_binding_mismatch -q`
  - Failed because continuation recovery was `none`.
- Batch GREEN:
  - Same command.
  - Failed once because continuation recovery omitted `next_params`; fixed by surfacing `next_params`.
  - Final result: `1 passed in 0.26s`.
- Direct mismatch RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_chapter_generation_execution.py::test_execute_generate_chapter_with_approval_blocks_resource_binding_mismatch -q`
  - Failed because recovery did not select `prepare_generate_chapter_execution`.
- Direct GREEN:
  - Same command.
  - `1 passed in 0.12s`.
- Missing binding coverage:
  - Batch missing binding: `1 passed in 0.90s`.
  - Direct missing binding: `1 passed in 0.13s`.

## Verification

- Targeted regression:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_execute_longform_chapter_batch_blocks_resource_binding_mismatch backend\tests\test_writing_agent_runs.py::test_agent_run_execute_longform_chapter_batch_recovers_missing_resource_binding backend\tests\test_writing_agent_chapter_generation_execution.py::test_execute_generate_chapter_with_approval_blocks_resource_binding_mismatch backend\tests\test_writing_agent_chapter_generation_execution.py::test_execute_generate_chapter_with_approval_recovers_missing_resource_binding backend\tests\test_writing_agent_runs.py::test_agent_run_can_plan_recovery_tools_from_blocked_run backend\tests\test_writing_agent_runs.py::test_agent_run_can_execute_approved_longform_chapter_batch_once -q`
  - `6 passed in 0.72s`.
- Hygiene:
  - `git diff --check` passed.
  - API key scan found no matches in non-archived backend/frontend/docs paths.

## Subagent Review

Carson reviewed the plan read-only and confirmed the architecture direction:
- Keep execution guard logic unchanged.
- Recover binding drift to fresh prepare tools.
- Add missing binding test coverage.
- Assert recovery preview does not auto-execute writes.

Adopted items:
- Added `resource_binding_missing` tests for batch and direct paths.
- Added preview assertions for a single prepare tool and `safe_auto_execute is False`.

Deferred items:
- Recovery execute confirmation path that proves only prepare runs and no chapter is written.
- Old approval hash invalidation after re-prepare.

These are useful but broader than Phase148's minimum recovery policy change and should be considered for a follow-up phase if recovery execution is expanded.

## Novel Progress

No new novel chapter was generated in this phase. This phase improves the Agent's long-run reliability by turning stale resource bindings into explicit, safe recovery steps.

## Known Limits

- Batch binding recovery does not infer `affected_chapter_indexes` when the blocked output lacks a top-level `chapter_index`.
- Direct recovery refreshes approval/binding state only; it does not rerun a full writing readiness preflight.

## Next Recommendation

Add a recovery execution safety phase that confirms recovery execution can run prepare-only plans under `confirm_execute + recovery_plan_hash`, while proving write tools remain blocked until a fresh approval contract is explicitly used.
