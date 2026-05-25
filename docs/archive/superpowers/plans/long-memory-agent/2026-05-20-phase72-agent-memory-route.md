# Agent Memory Route Phase72 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only Agent memory route tool that tells the Writing Agent whether longform memory, retrieval, and optional context summary are ready for the next writing action.

**Architecture:** Do not create a new memory system in this phase. Compose existing `longform_memory`, `athena_retrieval`, and `summarize_longform_context` services behind a compact Agent-facing route. Register it as an internal, read-only, non-blocking Agent tool so later planning can call one tool before choosing generation, repair, or review.

**Tech Stack:** FastAPI-independent service function, existing Writing Agent tool registry/executor, pytest.

---

## Context

The long-term goal is to turn novelv3 into a specialized writing Agent service. The user corrected that this is broader than slash commands: existing modules must become Agent-callable services/tools.

The current tool layer already has:

- `summarize_longform_context`
- `repair_longform_maintenance`
- retrieval and longform diagnostics exposed as API endpoints

Missing piece: a unified read-only Agent route that answers, "Can the Agent trust current memory/retrieval for this writing action, and what tool should it call next?"

## Reference Assimilation

- `openclaw`: planning should start from observable environment/state probes.
- `hermes-agent`: tools should return compact structured state and recommended next actions.
- `openhuman`: memory should be layered; route decisions should not directly mutate stored facts.

## Files

- Create `backend/app/services/writing_agent/agent_memory_route.py`
  - Compose longform memory diagnostics, maintenance diagnostics, retrieval diagnostics, and optional context summary.
  - Return a compact route decision and recommended tools.
- Modify `backend/app/services/writing_agent/tool_registry.py`
  - Add `inspect_agent_memory_route` descriptor.
- Modify `backend/app/services/writing_agent/tool_executor.py`
  - Add adapter and metadata.
- Modify `backend/tests/test_writing_agent_tool_registry.py`
  - Assert tool contract, target type, category, and non-blocking visibility.
- Modify `backend/tests/test_writing_agent_tool_executor.py`
  - Assert static adapter registration/metadata.
  - Assert executor dispatches the tool to the service.
- Add Phase72 report under `docs/superpowers/notes/long-memory-agent/`.

## Task 1: RED Registry Tests

- [ ] Add registry expectations:

```python
assert "inspect_agent_memory_route" in allowed_tool_names()
assert target_type_for_tool("inspect_agent_memory_route") == "agent_memory_route"
assert "inspect_agent_memory_route" in non_blocking_report_tool_names()
```

- [ ] Add dedicated descriptor test:

```python
def test_agent_tool_registry_includes_inspect_agent_memory_route():
    descriptor = get_agent_tool_descriptor("inspect_agent_memory_route")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "longform_memory"
    assert descriptor.target_type == "agent_memory_route"
    assert descriptor.input_schema["properties"]["chapter_index"]["minimum"] == 1
    assert descriptor.input_schema["properties"]["include_context_summary"]["type"] == "boolean"
```

- [ ] Run RED:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py -q -k "memory_route or unique_names"
```

Expected before implementation: failures because the tool is missing.

## Task 2: RED Executor Tests

- [ ] Add adapter name and metadata expectations.
- [ ] Add dispatch test using monkeypatch:

```python
@pytest.mark.asyncio
async def test_tool_executor_dispatches_inspect_agent_memory_route_adapter(db_session, monkeypatch):
    project = Project(name="Executor Memory Route")
    db_session.add(project)
    db_session.commit()
    calls = []

    def fake_route(db, project_id, *, chapter_index, query, include_context_summary):
        calls.append((project_id, chapter_index, query, include_context_summary))
        return {"status": "completed", "route": {"status": "ready"}}

    monkeypatch.setattr("app.services.writing_agent.agent_memory_route.inspect_agent_memory_route", fake_route)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="inspect_agent_memory_route",
            params={"chapter_index": "12", "query": "父亲失踪", "include_context_summary": True},
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "completed", "route": {"status": "ready"}}
    assert calls == [(project.id, 12, "父亲失踪", True)]
```

## Task 3: Service Implementation

- [ ] Create `agent_memory_route.py` with:

```python
def inspect_agent_memory_route(
    db: Session,
    project_id: str,
    *,
    chapter_index: int | None = None,
    query: str | None = None,
    include_context_summary: bool = False,
) -> dict[str, Any]:
```

- [ ] The service must call:
  - `get_longform_memory_diagnostics`
  - `get_longform_maintenance_diagnostics`
  - `get_retrieval_diagnostics`
  - `summarize_longform_context` only when `chapter_index` and `include_context_summary` are set
- [ ] Route decision:
  - `blocked` when maintenance `ready_for_writing` is false
  - `ready` when maintenance is ready
- [ ] Recommended tools:
  - include `repair_longform_maintenance` when blocked
  - include `summarize_longform_context` when ready and no context summary was requested
  - include `preflight_writing` when ready

## Task 4: GREEN Verification

- [ ] Run focused tests:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py -q -k "memory_route or static_adapter_names_are_report_or_agent_native_tools or lists_unhandled_internal_tools_for_migration_tracking"
```

- [ ] Run related Agent tool tests:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py -q
```

- [ ] Run static checks:

```powershell
git diff --check
rg -l "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

## Boundaries

Do:

- keep this tool read-only;
- use existing memory and retrieval services;
- make the route decision compact and JSON-safe;
- keep it available to Agent planning as a non-blocking report.

Do not:

- create a new database table;
- mutate memory, retrieval, or world facts;
- run real model generation;
- add frontend UI in this phase.
