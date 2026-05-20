# Phase42 Report: Agent Step Trace

## Phase Goal

Make Writing Agent executions traceable at the step level.

Phase41 added deterministic planning and explicit auto-plan execution. Phase42 carries that planner intent into each executed tool request and adds a normalized result envelope to each step output.

## Implemented

- Extended `WritingAgentToolRequest` with optional `planner` metadata.
- Updated `planner.py` so every planner-produced tool request includes:
  - planner step index;
  - reason;
  - missing-dependency strategy;
  - failure strategy;
  - expected output;
  - post-generation flag;
  - planner version.
- Updated `run_service.py` so `WritingAgentStep.input` persists planner metadata.
- Added `agent_tool_result` envelope to step outputs on success, blocked, and failed outputs when an output payload exists.
- Added tests proving:
  - planner output tools include metadata;
  - auto-planned run steps persist planner reasons;
  - generated step output exposes normalized `agent_tool_result`;
  - post-generation review steps are traceable.

## Why This Helps Agentization

The Agent now has a stable execution trace surface:

- why a tool was called;
- what the planner expected from it;
- what should happen if dependencies or execution fail;
- whether the step was a post-generation follow-up;
- what result status the tool returned.

This makes later retry logic, task queue recovery, quality dashboards, and self-optimization possible without parsing tool-specific output shapes.

## Validation

Validation level: T1/T2 boundary.

Focused red/green command:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_planner.py tests\test_writing_agent_runs.py -q -k "ready_next_chapter_tool_chain or auto_plan_executes"
```

Result:

```text
2 passed, 116 deselected
```

Module verification:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_planner.py tests\test_writing_agent_tool_registry.py tests\test_writing_agent_runs.py -q
```

Result:

```text
121 passed
```

Static checks:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

Result:

```text
git diff --check: passed
secret scan: no matches
```

## Current Limits

- The normalized result envelope is embedded in JSON output, not yet first-class database rows.
- It does not yet include elapsed time, output size, retry count, or model cost.
- Failed steps without an output payload still rely on `step.error`.
- There is still no reusable executor object per registry descriptor.

## Next Phase Recommendation

Phase43 should start splitting execution responsibilities:

- create registry-backed executor wrappers for internal tools;
- normalize blocked/failed outputs even when a tool returns no output;
- add elapsed time/output size fields to `agent_tool_result`;
- use the envelope to drive basic recovery decisions for missing setup/storyline/outline.
