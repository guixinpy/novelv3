# Agent Trace Audit Phase73 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only Agent trace audit tool that summarizes a Writing Agent run, its steps, model call traces, context blocks, failure state, and recommended next action.

**Architecture:** Compose existing `WritingAgentRun`, `WritingAgentStep`, and `AIModelCallTrace` records into one compact audit projection. Register it as an internal, read-only, non-blocking Agent tool. This phase does not create new persistence or UI; it gives the Agent a service-level way to explain and diagnose its own execution.

**Tech Stack:** SQLAlchemy models, Writing Agent tool registry/executor, pytest.

---

## Context

The long-term goal requires an auditable writing Agent, not just a set of generation APIs. Existing run details expose raw steps, and existing model trace APIs expose trace rows, but the Agent lacks a compact tool that can answer:

- What did this run try to do?
- Which tools executed?
- Which model traces were involved?
- Which context blocks were used?
- Where did it fail or block?
- What should the Agent call next?

## Reference Assimilation

- `openclaw`: executions should be explainable through control-plane history.
- `hermes-agent`: run/step/tool traces should be inspectable by the Agent itself.
- `openhuman`: memory/context evidence should be summarized without exposing oversized raw context by default.

## Files

- Create `backend/app/services/writing_agent/agent_trace_audit.py`
  - Build compact audit projection from run, steps, and traces.
- Modify `backend/app/services/writing_agent/tool_registry.py`
  - Add `inspect_agent_trace_audit` descriptor.
- Modify `backend/app/services/writing_agent/tool_executor.py`
  - Add adapter and metadata.
- Modify `backend/tests/test_writing_agent_tool_registry.py`
  - Assert descriptor and target type.
- Modify `backend/tests/test_writing_agent_tool_executor.py`
  - Assert adapter metadata and dispatch.
- Add `backend/tests/test_writing_agent_trace_audit.py`
  - Service-level tests for successful and failed/blocked runs.
- Add Phase73 report under `docs/superpowers/notes/long-memory-agent/`.

## Task 1: RED Registry And Executor Tests

- [ ] Add registry expectations:

```python
assert "inspect_agent_trace_audit" in allowed_tool_names()
assert target_type_for_tool("inspect_agent_trace_audit") == "agent_trace_audit"
assert "inspect_agent_trace_audit" in non_blocking_report_tool_names()
```

- [ ] Add executor adapter metadata expectation:

```python
assert writing_agent_tool_adapter_metadata("inspect_agent_trace_audit") == {
    "tool_name": "inspect_agent_trace_audit",
    "adapter_type": "static",
    "category": "trace",
    "mutability": "read",
    "handler_name": "_inspect_agent_trace_audit",
}
```

- [ ] Run RED:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py -q -k "trace_audit or static_adapter_names_are_report_or_agent_native_tools or lists_unhandled_internal_tools_for_migration_tracking"
```

Expected before implementation: failures because the tool descriptor and adapter are missing.

## Task 2: Service Tests

- [ ] Add service test for a successful run:
  - create project;
  - create `WritingAgentRun`;
  - create `AIModelCallTrace` with context blocks;
  - create successful `WritingAgentStep` referencing trace;
  - assert audit has run summary, one step, one trace, context summary, no failure.
- [ ] Add service test for a blocked run:
  - create blocked run and step with `agent_tool_result.recovery.next_tool`;
  - assert audit status is `blocked` and recommended action contains that next tool.

## Task 3: Implementation

- [ ] Create `inspect_agent_trace_audit()`:

```python
def inspect_agent_trace_audit(
    db: Session,
    project_id: str,
    *,
    run_id: str | None = None,
    chapter_index: int | None = None,
    task_id: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
```

- [ ] Lookup priority:
  - explicit `run_id`;
  - latest run with `background_task_id == task_id`;
  - latest run with a step for `chapter_index`;
  - latest run in project.
- [ ] Return compact:
  - `audit.status`;
  - `run`;
  - `steps`;
  - `traces`;
  - `context`;
  - `failure`;
  - `recommended_actions`;
  - `trace` metadata for this audit tool.
- [ ] Keep context compact:
  - include block keys, titles, char counts, source count;
  - do not include full context text.

## Task 4: GREEN Verification

- [ ] Run focused tests:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_trace_audit.py tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py -q -k "trace_audit or static_adapter_names_are_report_or_agent_native_tools or lists_unhandled_internal_tools_for_migration_tracking"
```

- [ ] Run all Writing Agent tests:

```powershell
cd backend
$files = Get-ChildItem tests -Filter "test_writing_agent_*.py" | ForEach-Object { $_.FullName }; .venv\Scripts\python.exe -m pytest @files tests\test_athena_ontology_agent.py -q
```

- [ ] Static checks:

```powershell
git diff --check
rg -l "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

## Boundaries

Do:

- keep audit read-only;
- summarize traces compactly;
- support run/chapter/task lookup;
- expose recommended next action when existing recovery metadata has it.

Do not:

- store new audit rows;
- expose raw prompt/context content by default;
- mutate runs, steps, traces, tasks, memory, or world facts;
- add frontend UI in this phase.
