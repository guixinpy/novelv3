# Phase145 Execution Binding Guard Report

## Objective

Block approved mutating Writing Agent execution if the approved `resource_binding` does not match the chapter resource about to be written.

## Implementation

- Added `verify_resource_binding_target()` in `backend/app/services/writing_agent/agent_step_binding.py`.
- Direct chapter execution now verifies the approved `generate_chapter -> chapter:{chapter_index}` binding before calling the chapter generation tool.
- Longform batch execution now performs the same guard before dispatching `ActionExecutionService.execute("generate_chapter")`.
- Success outputs now include `execution_resource_binding`.
- Blocked outputs include `execution_resource_binding`, `agent_plan_approval_verification`, and `approval_verification_event`.
- Tool registry output schemas were updated for:
  - `execute_generate_chapter_with_approval`
  - `execute_longform_chapter_batch`

## TDD Evidence

- Helper RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_step_binding.py -q`
  - Failed because `verify_resource_binding_target` was missing.
- Helper GREEN:
  - Same command.
  - `6 passed in 0.03s`
- Direct execution RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_chapter_generation_execution.py::test_execute_generate_chapter_with_approval_runs_after_contract_verification backend\tests\test_writing_agent_chapter_generation_execution.py::test_execute_generate_chapter_with_approval_blocks_resource_binding_mismatch -q`
  - Failed on missing `execution_resource_binding` and unblocked mismatch execution.
- Direct execution GREEN:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_chapter_generation_execution.py -q`
  - `5 passed in 0.39s`
- Batch execution RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_can_execute_approved_longform_chapter_batch_once backend\tests\test_writing_agent_runs.py::test_agent_run_execute_longform_chapter_batch_blocks_resource_binding_mismatch -q`
  - Failed on missing `execution_resource_binding` and unguarded mismatch execution.
- Batch execution GREEN:
  - Same command.
  - `2 passed in 0.49s`
- Tool registry RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_tool_registry.py::test_agent_tool_registry_includes_approved_direct_chapter_generation_tools backend\tests\test_writing_agent_tool_registry.py::test_agent_tool_registry_includes_execute_longform_chapter_batch -q`
  - Failed because output schemas did not expose execution binding fields.
- Tool registry GREEN:
  - Same command.
  - `2 passed in 0.03s`

## Verification

- Targeted regression:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_step_binding.py backend\tests\test_writing_agent_chapter_generation_execution.py backend\tests\test_writing_agent_runs.py::test_agent_run_can_execute_approved_longform_chapter_batch_once backend\tests\test_writing_agent_runs.py::test_agent_run_execute_longform_chapter_batch_blocks_resource_binding_mismatch backend\tests\test_writing_agent_approval_contract.py backend\tests\test_writing_agent_trace_audit.py backend\tests\test_writing_agent_tool_registry.py::test_agent_tool_registry_includes_approved_direct_chapter_generation_tools backend\tests\test_writing_agent_tool_registry.py::test_agent_tool_registry_includes_execute_longform_chapter_batch -q`
  - `32 passed in 1.09s`
- Hygiene:
  - `git diff --check` passed.
  - API key scan found no matches in non-archived backend/frontend/docs paths.

## Subagent Review

An explorer reviewed the plan and flagged that both direct and batch execution must be guarded, and that tool registry schemas must expose the new execution binding output. Both findings were incorporated in this phase.

## Novel Progress

No new novel chapter was generated in this phase. This phase narrowed the write-execution trust boundary so future autonomous generation can safely prove that approved write targets and actual write targets match.

## Known Limits

- The guard currently accepts any matching `generate_chapter` resource binding. Future multi-write plans should bind by exact step or `tool_call_id`.
- `resource_binding` is still contract/audit output, not a first-class persisted `WritingAgentStep` column.
- Existing prepared tasks from before Phase144/145 may need to be prepared again to include binding metadata.

## Next Recommendation

Persist `tool_call_id` and bounded `resource_binding` on `WritingAgentStep`, then expose them in trace audit and run-step summaries without relying only on nested tool output.
