# Agent Event Projection Slice

## Scope

Task 9 locks the event/task queue boundary as a read-only projection. It does
not add a new event bus or event table. The projection derives causal events
from existing `BackgroundTask`, `WritingAgentRun`, and `WritingAgentStep`
records.

## Implementation

- Added `inspect_agent_event_projection(...)` with `projection_only` boundary
  metadata.
- Projected task lifecycle events from `BackgroundTask`.
- Projected run lifecycle events from `WritingAgentRun`.
- Projected `tool_started`, `tool_completed`, and `tool_error` events from
  `WritingAgentStep`.
- Added `event_projection_summary_for_task(...)` to `inspect_agent_job_projection`.
- Exposed `inspect_agent_event_projection` as an internal read-only task queue
  tool.

## Verification

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_event_projection.py -q
# 2 passed

backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_event_projection.py backend\tests\test_writing_agent_job_projection.py backend\tests\test_writing_agent_tool_registry.py -q
# 74 passed

backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_tool_executor.py -k "agent_job_projection or agent_event_projection or describe_agent_tools" -q
# 6 passed, 153 deselected

git diff --check
# no output
```

## Boundary

The current dogfood hypothesis is that projection gives enough causality for
recovery and diagnostics. Persisted events should only be added if real
multi-chapter dogfood shows missing causality or ordering evidence.
