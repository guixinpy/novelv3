# Phase144 Tool Call Resource Binding Report

## Objective

Bind mutating Writing Agent write steps to stable server-derived `tool_call_id` and bounded `resource_binding` metadata, so approval, execution evidence, and trace audit can identify which planned tool call targeted which resource.

## Implementation

- Added `backend/app/services/writing_agent/agent_step_binding.py`.
- Added deterministic `toolcall:<sha>` identity derived from project id, plan id, step id, step index, tool name, target type, and target id.
- Added bounded `resource_binding` summary fields:
  - `tool_call_id`
  - `tool_name`
  - `target_type`
  - `target_id`
  - `source_plan_id`
  - `source_step_id`
  - `binding_source`
- Attached binding fields to mutating write steps in approval contracts.
- Exposed binding fields in direct `prepare_generate_chapter_execution` output and registry schema.
- Added binding summaries to approval verification events and trace audit event chains.
- Kept the phase contract-level and audit-level only. No database migration or persisted step columns were added.

## TDD Evidence

- RED helper test:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_step_binding.py -q`
  - Failed with `ModuleNotFoundError` before helper implementation.
- GREEN helper test:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_step_binding.py -q`
  - `3 passed in 0.04s`
- RED approval contract tests:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_approval_contract.py::test_approval_contract_attaches_mutation_fingerprint_to_write_steps backend\tests\test_writing_agent_approval_contract.py::test_verify_approval_contract_accepts_matching_hash -q`
  - Failed on missing `tool_call_id` and `resource_binding_count`.
- GREEN approval contract tests:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_approval_contract.py -q`
  - `14 passed in 0.08s`
- RED direct prepare/schema tests:
  - Failed on missing `tool_call_id` in direct prepare output and registry schema.
- GREEN direct prepare/schema tests:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_chapter_generation_execution.py backend\tests\test_writing_agent_tool_registry.py::test_agent_tool_registry_includes_approved_direct_chapter_generation_tools -q`
  - `5 passed in 0.41s`
- RED event/audit tests:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_can_execute_approved_longform_chapter_batch_once backend\tests\test_writing_agent_trace_audit.py::test_inspect_agent_trace_audit_includes_dialog_approval_events_without_raw_hash -q`
  - Failed on missing `tool_call_ids`.
- GREEN event/audit tests:
  - Same command.
  - `2 passed in 0.49s`

## Verification

- Targeted regression:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_step_binding.py backend\tests\test_writing_agent_approval_contract.py backend\tests\test_writing_agent_chapter_generation_execution.py backend\tests\test_writing_agent_tool_registry.py backend\tests\test_writing_agent_trace_audit.py backend\tests\test_writing_agent_runs.py::test_agent_run_can_execute_approved_longform_chapter_batch_once backend\tests\test_writing_agent_mutation_fingerprint.py -q`
  - `65 passed in 1.30s`

## Novel Progress

No new novel chapter was generated in this phase. This phase hardened the Agent approval/audit substrate needed before longer autonomous writing loops can safely dispatch mutating tools.

## Known Limits

- `tool_call_id` and `resource_binding` are not persisted as first-class `WritingAgentStep` columns.
- Execution does not yet perform a hard runtime comparison between expected binding and executed target.
- Frontend rendering for binding/audit details was not added in this phase.

## Next Recommendation

Add execution-time binding comparison for approved mutating tools, then consider persisting `tool_call_id` and `resource_binding` on `WritingAgentStep` through an Alembic migration once the contract shape stabilizes.
