# Phase112 Approval Tool Metadata Helper Plan

## Objective

Extract the approval tool metadata projection from `tool_executor.py` into a small neutral helper so future Agent write execution paths can reuse the Phase110/111 approval drift gate without importing executor internals.

## Assumptions

- Phase111's execution gate is correct: batch execution should receive runtime tool metadata through a narrow provider and block when approval evidence is missing or drifted.
- `tool_executor.py` can still own concrete adapter registration for now.
- The new helper should depend on the stable tool descriptor/contract modules, not on executor adapter tables.
- This phase is an extraction and test hardening step, not a redesign of the approval contract or task queue.

## Scope

1. Add a neutral helper under `backend/app/services/writing_agent/` that:
   - accepts an Agent plan dict,
   - accepts optional adapter metadata by tool name,
   - selects only write or confirmation-required steps,
   - projects `tool_exists`, `adapter_exists`, `adapter_type`, `handler_name`, `mutability`, `requires_confirmation`, and required input fields.
2. Add focused tests for the helper before implementation.
3. Refactor `tool_executor.py` so `_approval_tool_metadata_by_name` delegates to the helper while preserving current behavior.
4. Run targeted T1 verification for approval contracts, tool executor dispatch, tool registry, and batch execution gates.

## Out Of Scope

- Moving `_STATIC_TOOL_ADAPTERS` out of `tool_executor.py`.
- Changing approval contract hash semantics.
- Changing `batch_execution.py` persistence or execution flow.
- Adding new autonomous generation behavior.
- Full frontend or end-to-end test runs.

## Verification Plan

- T0 RED:
  - Run the new helper test file before implementation and confirm it fails due to the missing module/helper.
- T0 GREEN:
  - Run the helper test file after implementation.
- T1 regression:
  - `test_writing_agent_approval_tool_metadata.py`
  - `test_writing_agent_tool_executor.py`
  - `test_writing_agent_approval_contract.py`
  - `test_writing_agent_tool_registry.py`
  - focused longform batch execution tests in `test_writing_agent_runs.py`
- Hygiene:
  - `git diff --check`
  - secret scan over `backend` and active `docs`

## Success Criteria

- Helper tests cover read-step filtering, known write tool projection, missing adapter projection, and unknown write tool projection.
- Existing Phase111 execution provider behavior remains intact.
- Batch execution approval verification still receives enough metadata to detect missing or drifted write tool contracts.
