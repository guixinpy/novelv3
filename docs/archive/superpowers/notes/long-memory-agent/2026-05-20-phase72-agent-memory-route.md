# Phase72 Report: Agent Memory Route

## Summary

Phase72 adds a read-only Agent memory route tool: `inspect_agent_memory_route`.

This phase moves the project further from "page/API calls" toward "Agent-callable services". The tool composes existing longform memory diagnostics, maintenance diagnostics, retrieval diagnostics, and optional longform context summary into one Agent-facing decision:

- memory route is ready;
- memory route is blocked by stale/missing longform memory or retrieval index;
- Agent should repair memory;
- Agent should summarize context;
- Agent can proceed to generation preflight.

No new database table was added and no memory or world facts are mutated by this tool.

## Why This Matters

The user clarified that the goal is not just slash-command adaptation. The whole project must become a writing Agent service. For low-detail user intent, the Agent must decide which module/tool to call before generating.

Before this phase, the Agent could call `summarize_longform_context` and `repair_longform_maintenance`, but it had no compact route-level answer to: "Is memory usable right now, and what should I do next?"

## Changes

- Added `backend/app/services/writing_agent/agent_memory_route.py`.
- Added `inspect_agent_memory_route` to the Writing Agent tool registry.
- Added executor adapter `_inspect_agent_memory_route`.
- Added service-level tests for blocked and ready route decisions.
- Added registry and executor tests.

## Result Contract

Blocked route example:

```json
{
  "status": "completed",
  "route": {
    "status": "blocked",
    "reason": "longform_memory_needs_maintenance",
    "can_use_longform_context": false,
    "recommended_tools": ["repair_longform_maintenance"]
  },
  "diagnostics": [
    {
      "code": "longform_memory_needs_maintenance",
      "severity": "warning"
    }
  ]
}
```

Ready route example:

```json
{
  "status": "completed",
  "route": {
    "status": "ready",
    "reason": "longform_memory_ready",
    "can_use_longform_context": true,
    "recommended_tools": ["summarize_longform_context", "preflight_writing"]
  }
}
```

## Tool Contract

Tool name:

```text
inspect_agent_memory_route
```

Category:

```text
longform_memory
```

Target type:

```text
agent_memory_route
```

Mutability:

```text
read
```

Inputs:

- `chapter_index`
- `query`
- `include_context_summary`

Outputs:

- `route`
- `longform_memory`
- `longform_maintenance`
- `retrieval`
- `diagnostics`
- optional `context_summary`

## Verification

RED before implementation:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py -q -k "memory_route or static_adapter_names_are_report_or_agent_native_tools or lists_unhandled_internal_tools_for_migration_tracking"
```

Result before implementation: `4 failed, 1 passed`; failures showed the tool descriptor, adapter metadata, and module were missing.

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py -q -k "memory_route or static_adapter_names_are_report_or_agent_native_tools or lists_unhandled_internal_tools_for_migration_tracking"
```

Result: `5 passed, 41 deselected in 0.17s`.

Service and tool regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_memory_route.py tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py -q
```

Result: `48 passed in 1.75s`.

All Writing Agent related tests:

```powershell
cd backend
$files = Get-ChildItem tests -Filter "test_writing_agent_*.py" | ForEach-Object { $_.FullName }; .venv\Scripts\python.exe -m pytest @files tests\test_athena_ontology_agent.py -q
```

Result: `208 passed in 22.10s`.

Static checks:

```powershell
git diff --check
rg -l "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

Result:

- `git diff --check` passed with no output.
- secret scan returned no matches.

## Novel Progress

No production novel chapter was generated in this phase. The phase strengthens the Agent's ability to decide whether longform memory is reliable before the next dogfood generation step.

## Fixed Issues

- Agent lacked one compact memory/retrieval route decision before generation.
- Agent planning had to choose between context summary and maintenance without a unified readiness probe.

## Remaining Boundary

This is a read-only route. It does not yet:

- automatically repair memory;
- perform generation preflight;
- choose and execute a full tool chain;
- persist author/project knowledge base memories.

Next recommended phases:

1. Add Trace/context audit tool for run/chapter/task explanations.
2. Add read-only world model fact/query/impact route.
3. Convert generic background tasks into clearer Agent job projections.
4. Start the minimum Knowledge Base loop for author memory, project strategy, and self-optimization experience.
