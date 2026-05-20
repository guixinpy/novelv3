# Phase43 Report: Tool Executor Wrapper

## Phase Goal

Start separating Writing Agent tool execution from `run_service.py` so existing modules can progressively become Agent-callable tools with stable contracts.

This phase is intentionally narrow: it creates the executor wrapper and normalizes failure output, without moving generation, revision, or world-model mutation tools yet.

## Implemented

- Added `backend/app/services/writing_agent/tool_executor.py`.
- Added `WritingAgentToolContext` and `WritingAgentToolExecutionResult`.
- Added `execute_writing_agent_tool(...)` for Agent-native internal tools:
  - `describe_agent_tools`;
  - `plan_writing_agent_run`;
  - `preflight_writing` through an injected callback.
- Updated `run_service.py` so `_execute_tool` delegates to the executor first, then falls back to the existing action-service/internal dispatcher.
- Removed duplicated inline execution branches for the three migrated tools.
- Normalized failed and blocked step outputs when no tool output exists:
  - fallback output includes `status` and `error`;
  - fallback output includes the existing `agent_tool_result` envelope.
- Added tests proving:
  - executor handles Agent-native tools;
  - executor leaves legacy generation tools unhandled;
  - unsupported tools now produce normalized failed step output.

## Why This Helps Agentization

The system now has the first explicit execution boundary between:

- run lifecycle management;
- Agent-native tool execution;
- legacy action execution.

This is the required foundation for module toolization. Future phases can move Athena, knowledge base, retrieval, review, and task queue tools into adapters one by one while preserving run lifecycle behavior and verification scope.

The normalized failed/blocked output also gives future recovery logic a stable surface. The Agent no longer has to infer failed-step structure from `step.error` alone.

## Validation

Validation level: T1.

Focused RED command:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py -q -k "tool_executor or unsupported_tool"
```

RED result:

```text
ModuleNotFoundError: No module named 'app.services.writing_agent.tool_executor'
```

Focused GREEN command:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py -q -k "tool_executor or unsupported_tool"
```

GREEN result:

```text
5 passed, 114 deselected
```

Module verification:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py tests\test_writing_agent_planner.py tests\test_writing_agent_tool_registry.py -q
```

Result:

```text
126 passed
```

Static check:

```powershell
git diff --check
```

Result:

```text
exit 0; warning only: backend/tests/test_writing_agent_runs.py CRLF will be replaced by LF the next time Git touches it
```

Secret scan:

```powershell
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

Result:

```text
exit 1; no matches
```

## Current Limits

- Only three Agent-native tools are routed through the new executor.
- Most internal tools are still implemented in `run_service.py`.
- Executor results do not yet include elapsed time, output size, retry metadata, or recovery advice.
- There is no per-descriptor adapter map yet.

## Next Phase Recommendation

Phase44 should turn this wrapper into a descriptor-driven adapter map:

- define one adapter entry per internal tool family;
- move safe read/report tools first;
- keep mutation-heavy world-model and revision tools behind targeted tests;
- extend `agent_tool_result` with elapsed time and output size;
- begin using normalized failure envelopes for planner recovery decisions.
