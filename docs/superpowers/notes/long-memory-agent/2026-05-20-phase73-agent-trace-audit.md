# Phase73 Report: Agent Trace Audit

## Summary

Phase73 adds a read-only Agent trace audit tool: `inspect_agent_trace_audit`.

This gives the Writing Agent a compact service-level way to inspect a run, its steps, linked model traces, context block metadata, failure state, and recommended recovery action.

The tool does not expose full raw context text by default and does not mutate any run, trace, task, memory, or world model data.

## Why This Matters

The long-term goal is a specialized writing Agent, not only a set of generation endpoints. A durable Agent must be able to explain and diagnose its own execution:

- what run was selected;
- which tools were executed;
- which model traces were involved;
- which context blocks were used;
- where the run failed or blocked;
- which next tool should be called.

Before this phase, this information existed across `WritingAgentRun`, `WritingAgentStep`, `AIModelCallTrace`, and raw API responses. Phase73 consolidates it into one Agent-callable audit service.

## Changes

- Added `backend/app/services/writing_agent/agent_trace_audit.py`.
- Added `inspect_agent_trace_audit` to the Writing Agent tool registry.
- Added executor adapter `_inspect_agent_trace_audit`.
- Added service-level tests for successful and blocked runs.
- Added registry and executor tests.

## Lookup Behavior

The audit service selects a run in this order:

1. explicit `run_id`;
2. latest run with matching `background_task_id`;
3. latest run with a step matching `chapter_index`;
4. latest run in the project;
5. no-run audit result if nothing matches.

## Result Contract

The output includes:

- `audit`: compact status, reason, counts;
- `run`: run summary;
- `steps`: compact step summaries;
- `traces`: compact model trace summaries;
- `context`: context block metadata without raw context text;
- `failure`: failed/blocked tool summary;
- `recommended_actions`: next suggested tool when recovery metadata is available.

Blocked example:

```json
{
  "status": "completed",
  "audit": {
    "status": "blocked",
    "reason": "longform_memory_needs_maintenance"
  },
  "failure": {
    "tool_name": "inspect_agent_memory_route",
    "message": "长篇记忆未就绪"
  },
  "recommended_actions": [
    {
      "tool_name": "repair_longform_maintenance",
      "reason_code": "longform_memory_needs_maintenance",
      "source_step_index": 1
    }
  ]
}
```

## Verification

RED before implementation:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py -q -k "trace_audit or static_adapter_names_are_report_or_agent_native_tools or lists_unhandled_internal_tools_for_migration_tracking"
```

Result before implementation: `4 failed, 1 passed`; failures showed the tool descriptor, adapter metadata, and module were missing.

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_trace_audit.py tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py -q -k "trace_audit or static_adapter_names_are_report_or_agent_native_tools or lists_unhandled_internal_tools_for_migration_tracking"
```

Result: `7 passed, 44 deselected in 0.33s`.

Trace/tool regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_trace_audit.py tests\test_writing_agent_memory_route.py tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py -q
```

Result: `53 passed in 1.64s`.

All Writing Agent related tests:

```powershell
cd backend
$files = Get-ChildItem tests -Filter "test_writing_agent_*.py" | ForEach-Object { $_.FullName }; .venv\Scripts\python.exe -m pytest @files tests\test_athena_ontology_agent.py -q
```

Result: `213 passed in 20.04s`.

## Novel Progress

No production novel chapter was generated in this phase. This phase improves the Agent's ability to audit long-running generation before the next dogfood generation cycle.

## Fixed Issues

- Agent lacked a compact run/step/trace/context audit tool.
- Recovery metadata existed inside step output but was not easily exposed as a next-action summary.
- Context block evidence was not available to the Agent without fetching raw trace detail.

## Remaining Boundary

This phase is read-only. It does not:

- persist audit rows;
- modify failed runs;
- execute recovery;
- add a frontend audit view;
- perform world-model impact analysis.

Recommended next phases:

1. Add read-only world model fact/query/impact route.
2. Convert generic background tasks into clearer Agent job projections.
3. Start the minimum Knowledge Base loop for author memory, project strategy, and self-optimization experience.
4. Resume real dogfood generation using `inspect_agent_memory_route` and `inspect_agent_trace_audit` before generation.
