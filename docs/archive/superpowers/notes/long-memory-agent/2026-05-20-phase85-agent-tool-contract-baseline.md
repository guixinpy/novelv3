# Phase85 Report: Agent Tool Contract Baseline

## Summary

Phase85 created the first formal Writing Agent tool-contract snapshot for novelv3.

The goal was not to rewrite a large module immediately. The goal was to make the current Agent tool surface measurable, so future Hermes, Athena, world-model, knowledge-base, slash-command, review, task-queue, and Trace refactors can be judged against Agent-native contracts instead of UI-era module boundaries.

Implemented:

- Added internal read-only tool `inspect_agent_tool_contracts`.
- Added `backend/app/services/writing_agent/tool_contracts.py`.
- Exposed adapter metadata and executor handling for the new tool.
- Added focused registry and executor tests.
- Captured reference-project patterns from `openclaw`, `hermes-agent`, and `openhuman` as explicit alignment fields.

No chapter generation was performed in this phase.

## Reference Learning

Read-only subagent analysis extracted these portable patterns:

- From `openclaw`: tool descriptors should be separate from execution; visibility projection should be policy-driven; runtime validation and recovery paths are part of the tool contract; memory boundaries should be explicit.
- From `hermes-agent`: toolsets should be grouped by capability domain rather than UI group; multi-tool orchestration needs mutability, resource scope, parallel safety, confirmation, failure modes, and recommended recovery tools.
- From `openhuman`: registered tools, visible tools, and internal executor tools should be treated as different layers; permission level, result-size policy, event auditability, and bounded memory context should be first-class contract data.

The resulting snapshot exposes:

- visibility;
- mutability;
- permission level;
- side effects;
- confirmation requirement;
- parallel safety;
- resource scope;
- memory boundary;
- Trace requirement;
- result-size policy;
- adapter metadata;
- schema coverage;
- preconditions and postconditions;
- recovery tools;
- gap codes.

## Files Changed

- `backend/app/services/writing_agent/tool_contracts.py`
- `backend/app/services/writing_agent/tool_registry.py`
- `backend/app/services/writing_agent/tool_executor.py`
- `backend/tests/test_writing_agent_tool_registry.py`
- `backend/tests/test_writing_agent_tool_executor.py`
- `docs/superpowers/plans/long-memory-agent/2026-05-20-phase85-agent-tool-contract-baseline.md`

## Runtime Contract

New tool:

- name: `inspect_agent_tool_contracts`
- category: `preflight`
- target type: `agent_tool_contracts`
- internal: `true`
- non-blocking report: `true`
- mutability: `read`

Expected output:

- `status`
- `summary`
- `coverage`
- `tools`
- `gaps`
- `reference_alignment`
- `recommended_next_steps`

The tool is read-only and does not mutate project state.

## Validation

RED tests were added before implementation for:

- registry exposure of `inspect_agent_tool_contracts`;
- adapter metadata exposure;
- executor handling and contract snapshot contents.

Focused T1 checks:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_registry.py::test_agent_tool_registry_includes_inspect_agent_tool_contracts -q
```

Result: `1 passed`

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_exposes_inspect_agent_tool_contracts_adapter_metadata backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_handles_inspect_agent_tool_contracts -q
```

Result: `2 passed`

Related T1 slice:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py -q
```

Result after reviewer fix: `65 passed`

Independent review finding:

- A reviewer found that confirmation/hash-protected write tools were still reported as plain `write` in the contract snapshot because executor adapter metadata is intentionally low-level.
- Fixed in the contract layer: write tools with confirmation/hash fields, or guarded action prefixes such as `execute_`, `enqueue_`, `apply_`, and `route_`, are now reported as `guarded_write`.
- Added assertions for `enqueue_longform_chapter_batch`, `execute_longform_chapter_batch`, and `route_longform_chapter_batch_after_review`.
- Added compact-output coverage for `include_gap_details=false`.

## Findings

Fixed:

1. The Writing Agent now has a self-inspection tool for measuring whether existing modules have become Agent-callable tools.
2. Legacy action tools are now visible as contract gaps instead of being hidden inside planner behavior.
3. Tool contracts now expose Agent-critical fields that were previously implicit: mutability, permission, memory boundary, confirmation, Trace, recovery, and result-size policy.
4. Future refactors can prioritize by actual contract gaps such as `missing_agent_native_adapter`, `missing_confirmation_guard`, `missing_availability_checks`, and `output_schema_too_generic`.
5. Confirmation/hash-protected writes are distinguished from ordinary writes as `guarded_write`, which gives the planner a safer permission model.

Important current gaps surfaced by this phase:

- Several core generation and world-model write paths still rely on legacy actions rather than Agent-native adapters.
- Some write tools still need stronger explicit confirmation/hash gates.
- Several older outputs remain too generic for autonomous planner decisions.
- Slash-command era command shapes still need to be reinterpreted as Agent tool intents instead of user-facing command syntax.

## Next Phase Recommendation

Phase86 should use `inspect_agent_tool_contracts` as the planning input and start migrating the highest-impact legacy tools into Agent-native adapters.

Recommended order:

1. Convert chapter generation and revision planning from legacy action handling into explicit Agent tools with preflight, execute, post-review, and recovery contracts.
2. Convert world-model proposal writes into guarded Agent tools with confirmation/hash gates and Trace-visible outcomes.
3. Reframe the existing slash-command module as an intent router that produces tool plans, not as a separate command UX layer.
4. Keep using `openclaw`, `hermes-agent`, and `openhuman` as design references, but adapt only the patterns that improve novel-writing Agent autonomy.
