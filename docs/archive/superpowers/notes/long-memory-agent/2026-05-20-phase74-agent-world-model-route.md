# Phase74 Report: Agent World Model Route

## Summary

Phase74 adds a read-only Agent world-model route tool: `inspect_agent_world_model_route`.

The tool summarizes:

- current world model profile readiness;
- confirmed truth fact coverage;
- optional subject-specific fact preview;
- pending world-model proposal pressure;
- whether the Agent should proceed to preflight or stop for proposal review.

This moves Athena/world model further toward an Agent-callable service rather than a page-only/API-only subsystem.

## Why This Matters

For long-form novel generation, the Agent cannot rely on user prompts to manually enforce continuity. It must check world facts and pending proposal risk before generation or revision.

Before this phase, the system had world-model APIs and proposal review tools, but the Agent lacked one compact route-level answer:

```text
Can I safely use the world model for the next writing step, or must I resolve pending proposals first?
```

## Changes

- Added `backend/app/services/writing_agent/agent_world_model_route.py`.
- Added `inspect_agent_world_model_route` to the Writing Agent tool registry.
- Added executor adapter `_inspect_agent_world_model_route`.
- Added service-level tests:
  - missing profile blocks and recommends setup import;
  - ready profile with confirmed fact returns fact preview;
  - pending proposal blocks and recommends proposal review.
- Added registry and executor tests.

## Result Contract

Missing profile:

```json
{
  "route": {
    "status": "blocked",
    "reason": "missing_world_model_profile",
    "can_use_world_model": false
  },
  "recommended_actions": ["import_setup_world_model"]
}
```

Ready:

```json
{
  "route": {
    "status": "ready",
    "reason": "world_model_ready",
    "can_use_world_model": true,
    "pending_proposal_count": 0
  },
  "recommended_actions": ["preflight_writing"]
}
```

Pending proposals:

```json
{
  "route": {
    "status": "blocked",
    "reason": "pending_world_model_proposals",
    "can_use_world_model": true,
    "pending_proposal_count": 1
  },
  "recommended_actions": ["review_world_model_proposals"]
}
```

## Verification

RED before implementation:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_world_model_route.py tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py -q -k "world_model_route or static_adapter_names_are_report_or_agent_native_tools or lists_unhandled_internal_tools_for_migration_tracking"
```

Result before implementation: collection failed because `app.services.writing_agent.agent_world_model_route` did not exist.

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_world_model_route.py tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py -q -k "world_model_route or static_adapter_names_are_report_or_agent_native_tools or lists_unhandled_internal_tools_for_migration_tracking"
```

Result: `8 passed, 47 deselected in 0.33s`.

Related Athena/Agent regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_world_model_route.py tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py tests\test_athena_longform.py tests\test_athena_retrieval.py -q
```

Result: `113 passed in 6.53s`.

All Writing Agent related tests:

```powershell
cd backend
$files = Get-ChildItem tests -Filter "test_writing_agent_*.py" | ForEach-Object { $_.FullName }; .venv\Scripts\python.exe -m pytest @files tests\test_athena_ontology_agent.py -q
```

Result: `219 passed in 18.07s`.

## Novel Progress

No production novel chapter was generated in this phase. This phase strengthens the Agent's world-model safety gate before the next dogfood generation cycle.

## Fixed Issues

- Agent lacked a compact world-model readiness route.
- Pending proposal pressure was not exposed as a simple generation blocker.
- Confirmed world facts could not be retrieved by the Agent through a compact subject/chapter route.

## Remaining Boundary

This phase is read-only. It does not:

- apply or reject world-model proposals;
- mutate facts;
- call LLMs;
- add UI.

Recommended next phases:

1. Convert background tasks into clearer generic Agent job projections.
2. Start minimum Knowledge Base loop for author memory, project strategy, and self-optimization experience.
3. Resume real dogfood generation using memory route, trace audit, and world-model route before generation.
