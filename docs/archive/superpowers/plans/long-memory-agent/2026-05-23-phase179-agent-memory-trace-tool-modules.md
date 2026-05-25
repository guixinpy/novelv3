# Phase179 Agent Memory Trace Tool Modules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Writing Agent 的 Trace 审计、长篇记忆路由、上下文摘要和长篇维护修复工具拆成独立能力域模块。

**Architecture:** 继续沿用能力域模块化：`tool_registry.py` 只聚合 descriptor，`tool_executor.py` 只聚合 adapter。新增 `agent_memory_trace_tool_descriptors.py` 与 `agent_memory_trace_tool_adapters.py`，把 trace/read-memory/write-maintenance 相关工具集中管理，为后续长期记忆 Agent 自主读写与故障恢复做边界准备。

**Tech Stack:** Python 3、pytest、Writing Agent service layer。

---

## Files

- Create: `backend/app/services/writing_agent/agent_memory_trace_tool_descriptors.py`
  - Export `AGENT_MEMORY_TRACE_TOOL_DESCRIPTORS`.
  - Own trace / longform-memory / longform-maintenance descriptor schemas.
- Create: `backend/app/services/writing_agent/agent_memory_trace_tool_adapters.py`
  - Export `AGENT_MEMORY_TRACE_TOOL_ADAPTERS`.
  - Own adapter handlers and local helpers for optional integers and JSON-safe output.
- Modify: `backend/app/services/writing_agent/tool_registry.py`
  - Import and spread `AGENT_MEMORY_TRACE_TOOL_DESCRIPTORS`.
  - Remove inline memory/trace descriptor blocks.
- Modify: `backend/app/services/writing_agent/tool_executor.py`
  - Import and merge `AGENT_MEMORY_TRACE_TOOL_ADAPTERS`.
  - Remove inline memory/trace handlers and adapter entries.
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
  - Add descriptor module boundary test.
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
  - Add adapter module boundary test.

## Success Criteria

- `tool_registry.py` no longer defines these descriptors inline:
  - `inspect_agent_trace_audit`
  - `inspect_agent_memory_route`
  - `summarize_longform_context`
  - `repair_longform_maintenance`
- `tool_executor.py` no longer defines matching handlers inline.
- `repair_longform_maintenance` remains category=`maintenance`, mutability=`write`, and non-blocking false.
- Read-only memory/trace tools remain non-blocking reports.
- Existing dispatch and metadata tests remain green.

## Non-Scope

- Do not move longform batch/task queue tools; those already live in `longform_tool_descriptors.py` / `longform_tool_adapters.py`.
- Do not move `inspect_agent_job_projection` or `plan_chapter_conflict_recovery`; they are task queue tools.
- Do not move `backfill_outline_gaps`; it is narrative outline maintenance, not longform memory maintenance.
- Do not move generation tools.

## Tasks

### Task 1: RED Descriptor Boundary Test

- [x] Add import in `backend/tests/test_writing_agent_tool_registry.py`:

```python
from app.services.writing_agent.agent_memory_trace_tool_descriptors import AGENT_MEMORY_TRACE_TOOL_DESCRIPTORS
```

- [x] Add:

```python
def test_agent_memory_trace_tool_descriptors_live_in_dedicated_module():
    names = [descriptor.name for descriptor in AGENT_MEMORY_TRACE_TOOL_DESCRIPTORS]

    assert names == [
        "inspect_agent_trace_audit",
        "inspect_agent_memory_route",
        "summarize_longform_context",
        "repair_longform_maintenance",
    ]
    assert {descriptor.category for descriptor in AGENT_MEMORY_TRACE_TOOL_DESCRIPTORS} == {
        "trace",
        "longform_memory",
        "maintenance",
    }
    assert all(descriptor.internal for descriptor in AGENT_MEMORY_TRACE_TOOL_DESCRIPTORS)
    assert target_type_for_tool("inspect_agent_trace_audit") == "agent_trace_audit"
    assert target_type_for_tool("inspect_agent_memory_route") == "agent_memory_route"
    assert target_type_for_tool("summarize_longform_context") == "longform_context_summary"
    assert target_type_for_tool("repair_longform_maintenance") == "longform_maintenance"
    assert "inspect_agent_trace_audit" in non_blocking_report_tool_names()
    assert "repair_longform_maintenance" not in non_blocking_report_tool_names()
```

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_agent_memory_trace_tool_descriptors_live_in_dedicated_module -q
```

Expected: FAIL because `agent_memory_trace_tool_descriptors.py` does not exist.

### Task 2: RED Adapter Boundary Test

- [x] Add import in `backend/tests/test_writing_agent_tool_executor.py`:

```python
from app.services.writing_agent.agent_memory_trace_tool_adapters import AGENT_MEMORY_TRACE_TOOL_ADAPTERS
```

- [x] Add:

```python
def test_agent_memory_trace_tool_adapters_live_in_dedicated_module():
    names = list(AGENT_MEMORY_TRACE_TOOL_ADAPTERS)

    assert names == [
        "inspect_agent_trace_audit",
        "inspect_agent_memory_route",
        "summarize_longform_context",
        "repair_longform_maintenance",
    ]
    assert {adapter.category for adapter in AGENT_MEMORY_TRACE_TOOL_ADAPTERS.values()} == {
        "trace",
        "longform_memory",
        "maintenance",
    }
    assert AGENT_MEMORY_TRACE_TOOL_ADAPTERS["inspect_agent_trace_audit"].mutability == "read"
    assert AGENT_MEMORY_TRACE_TOOL_ADAPTERS["summarize_longform_context"].mutability == "read"
    assert AGENT_MEMORY_TRACE_TOOL_ADAPTERS["repair_longform_maintenance"].mutability == "write"
    assert (
        AGENT_MEMORY_TRACE_TOOL_ADAPTERS["repair_longform_maintenance"].handler.__name__
        == "_repair_longform_maintenance"
    )
```

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py::test_agent_memory_trace_tool_adapters_live_in_dedicated_module -q
```

Expected: FAIL because `agent_memory_trace_tool_adapters.py` does not exist.

### Task 3: Extract Memory/Trace Descriptors

- [x] Create `backend/app/services/writing_agent/agent_memory_trace_tool_descriptors.py`.
- [x] Use `AgentToolDescriptor` and `object_schema`.
- [x] Move the four descriptor blocks into `AGENT_MEMORY_TRACE_TOOL_DESCRIPTORS`.
- [x] In `tool_registry.py`, import and spread:

```python
from app.services.writing_agent.agent_memory_trace_tool_descriptors import AGENT_MEMORY_TRACE_TOOL_DESCRIPTORS

...
    *AGENT_MEMORY_TRACE_TOOL_DESCRIPTORS,
```

- [x] Remove inline memory/trace descriptor blocks from `tool_registry.py`.

### Task 4: Extract Memory/Trace Adapters

- [x] Create `backend/app/services/writing_agent/agent_memory_trace_tool_adapters.py`.
- [x] Move the four adapter handlers from `tool_executor.py`.
- [x] Add local helpers:

```python
def _json_safe_output(output: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(output, ensure_ascii=False, default=str))


def _optional_int(value: object) -> int | None:
    ...
```

- [x] Export `AGENT_MEMORY_TRACE_TOOL_ADAPTERS` with the four matching adapter entries.
- [x] In `tool_executor.py`, import and merge:

```python
from app.services.writing_agent.agent_memory_trace_tool_adapters import AGENT_MEMORY_TRACE_TOOL_ADAPTERS

...
_STATIC_TOOL_ADAPTERS.update(AGENT_MEMORY_TRACE_TOOL_ADAPTERS)
```

- [x] Remove inline memory/trace handlers and adapter entries from `tool_executor.py`.

### Task 5: Verification

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_agent_memory_trace_tool_descriptors_live_in_dedicated_module -q
pytest backend/tests/test_writing_agent_tool_executor.py::test_agent_memory_trace_tool_adapters_live_in_dedicated_module -q
```

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py -q
pytest backend/tests/test_writing_agent_tool_executor.py -k "agent_memory_trace or inspect_agent_memory_route or inspect_agent_trace_audit or summarize_longform_context or repair_longform_maintenance" -q
python -m compileall backend/app/services/writing_agent
```

### Task 6: Report, Hygiene, Commit, Push

- [x] Run:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

- [x] Write report:

```text
docs/superpowers/notes/long-memory-agent/2026-05-23-phase179-agent-memory-trace-tool-modules.md
```

- [x] Commit and push:

```powershell
git add backend/app/services/writing_agent/agent_memory_trace_tool_descriptors.py backend/app/services/writing_agent/agent_memory_trace_tool_adapters.py backend/app/services/writing_agent/tool_registry.py backend/app/services/writing_agent/tool_executor.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase179-agent-memory-trace-tool-modules.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase179-agent-memory-trace-tool-modules.md
git commit -m "refactor: split agent memory trace tools"
git push origin main
```
