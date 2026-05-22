# Phase107 Agent Plan Step Metadata Report

## Phase Summary

Phase107 added stable metadata to Writing Agent plans. Plans now expose a deterministic `plan_id`, every step exposes a deterministic `step_id`, and dialog-originated plans propagate `source_projection_id` from the intent projection into the planner trace and each step.

## Goal Alignment

- Moves the project toward an Agent core that can plan, audit, and later execute tool chains without relying on user-written long prompts.
- Keeps original modules toolized rather than preserving UI-era module boundaries.
- Adds approval-readiness metadata without changing runtime execution behavior.
- Continues the reference-project learning loop through a read-only subagent review of planning, approval, and trace patterns.

## Implemented

- Added `agent_tool_execution_metadata()` to `tool_contracts.py`.
- Added planner-level metadata:
  - `trace.plan_id`
  - `trace.source_projection_id`
- Added step-level metadata:
  - `step_id`
  - `plan_id`
  - `source_projection_id`
  - `mutability`
  - `requires_confirmation`
- Added the same metadata to each `tools[].planner` request payload.
- Updated `dialog_intent_planner.py` to pass dialog `projection_id` into the base planner.
- Added regression assertions for both direct planner calls and dialog-intent-originated plans.

## Design Notes

- This phase only decorates plan output; it does not add or enforce an approval gate.
- `requires_confirmation` is conservative planner metadata: write or guarded-write tools are marked true.
- The base planner does not import or depend on `IntentRouter`; dialog-specific source ids are optional.
- Existing `step_index`, tool order, dependency checks, and tool execution dispatch remain unchanged.

## Subagent Review

The read-only subagent recommended:

- Add `plan_id` and `step_id` now.
- Propagate `source_projection_id` only when dialog intent projection exists.
- Treat `mutability` and `requires_confirmation` as metadata only.
- Leave approval contracts, trace persistence, and runtime enforcement for later phases.

The implementation follows those constraints.

## Novel Progress

No novel chapter was generated in this phase. This phase improves the Agent planning substrate needed before long-running autonomous generation can safely execute or recover tool chains.

## Verification

Red test:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_planner.py backend/tests/test_writing_agent_tool_executor.py -k "ready_next_chapter_tool_chain or dialog_intent_agent_plan_for_chapter" -q
```

Initial result:

```text
2 failed
```

Green focused result:

```text
2 passed, 74 deselected
```

T1 module coverage:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_planner.py -q
```

Result:

```text
104 passed
```

Hygiene:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

Result:

```text
No whitespace errors. No active secret matches.
```

## Next Phase Recommendation

Phase108 should use the new metadata to create a read-only approval contract preview for planned write steps. It should produce a hash-bound confirmation payload, but still avoid changing actual execution behavior until the approval gate is explicitly wired.
