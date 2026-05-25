# Phase174 Longform Tool Adapter Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将后端长篇批次 Writing Agent static adapters 从通用 `tool_executor.py` 拆到独立模块，形成 descriptor 与 adapter 都按能力域组织的后端 Agent 工具结构。

**Architecture:** 新增 adapter 类型模块承载 `WritingAgentToolContext`、`WritingAgentToolAdapter` 等共享类型；新增 `longform_tool_adapters.py` 承载八个长篇批次 adapter handler 和 adapter map builder。`tool_executor.py` 保持公开执行入口、metadata 查询和静态 adapter 聚合职责。

**Tech Stack:** Python 3、pytest、Writing Agent service layer。

---

## Files

- Create: `backend/app/services/writing_agent/tool_adapter_types.py`
  - Own `PreflightWriting`、`StaticToolAdapterOutput`、`StaticToolAdapterHandler`。
  - Own `WritingAgentToolContext`、`WritingAgentToolExecutionResult`、`WritingAgentToolAdapter`。
- Create: `backend/app/services/writing_agent/longform_tool_adapters.py`
  - Export `build_longform_agent_tool_adapters(...)`.
  - Own the eight longform batch handlers and their local param parsing helper.
- Modify: `backend/app/services/writing_agent/tool_executor.py`
  - Import shared adapter types.
  - Import and merge longform adapter map.
  - Remove inline longform handlers and inline longform adapter entries.
  - Preserve current public imports of `WritingAgentToolContext` and `WritingAgentToolAdapter` from `tool_executor.py`.
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
  - Assert longform adapter map comes from the dedicated module.

## Success Criteria

- `tool_executor.py` no longer defines `_plan_longform_chapter_batch`, `_enqueue_longform_chapter_batch`, `_inspect_longform_chapter_batch`, `_execute_longform_chapter_batch_preflight`, `_prepare_longform_chapter_batch_execution`, `_execute_longform_chapter_batch`, `_review_longform_chapter_batch_execution`, or `_route_longform_chapter_batch_after_review`.
- `longform_tool_adapters.py` owns these handlers.
- `writing_agent_tool_adapter_metadata(...)` still returns the same tool names, categories, mutability, and handler names.
- `execute_writing_agent_tool(...)` still dispatches all longform tools.
- Existing imports from `tool_executor.py` remain stable.

## Tasks

### Task 1: Write Failing Adapter Module Test

- [x] In `backend/tests/test_writing_agent_tool_executor.py`, add:

```python
from app.services.writing_agent.longform_tool_adapters import build_longform_agent_tool_adapters
```

- [x] Add this test:

```python
def test_longform_tool_adapters_live_in_dedicated_module():
    adapters = build_longform_agent_tool_adapters(approval_tool_metadata_provider=lambda plan: {})
    names = list(adapters)

    assert names == [
        "plan_longform_chapter_batch",
        "enqueue_longform_chapter_batch",
        "inspect_longform_chapter_batch",
        "execute_longform_chapter_batch_preflight",
        "prepare_longform_chapter_batch_execution",
        "execute_longform_chapter_batch",
        "review_longform_chapter_batch_execution",
        "route_longform_chapter_batch_after_review",
    ]
    assert {adapter.category for adapter in adapters.values()} == {"task_queue"}
    assert adapters["plan_longform_chapter_batch"].mutability == "read"
    assert adapters["inspect_longform_chapter_batch"].mutability == "read"
    assert adapters["execute_longform_chapter_batch"].mutability == "write"
    assert adapters["execute_longform_chapter_batch"].handler.__name__ == "_execute_longform_chapter_batch"
```

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py::test_longform_tool_adapters_live_in_dedicated_module -q
```

Expected: FAIL because `app.services.writing_agent.longform_tool_adapters` does not exist yet.

### Task 2: Extract Shared Adapter Types

- [x] Create `backend/app/services/writing_agent/tool_adapter_types.py` with:

```python
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.schemas.writing_agent import WritingAgentToolRequest


PreflightWriting = Callable[[str, dict[str, Any]], dict[str, Any]]
StaticToolAdapterOutput = dict[str, Any] | Awaitable[dict[str, Any]]
StaticToolAdapterHandler = Callable[["WritingAgentToolContext", WritingAgentToolRequest], StaticToolAdapterOutput]


@dataclass(frozen=True)
class WritingAgentToolContext:
    db: Session
    project_id: str
    run_id: str | None = None


@dataclass(frozen=True)
class WritingAgentToolExecutionResult:
    handled: bool
    output: dict[str, Any] | None = None


@dataclass(frozen=True)
class WritingAgentToolAdapter:
    tool_name: str
    handler: StaticToolAdapterHandler
    category: str
    mutability: str
    adapter_type: str = "static"

    def to_metadata(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "adapter_type": self.adapter_type,
            "category": self.category,
            "mutability": self.mutability,
            "handler_name": self.handler.__name__,
        }
```

- [x] In `tool_executor.py`, remove the inline aliases/dataclasses and import them from `tool_adapter_types.py`.

### Task 3: Extract Longform Adapter Module

- [x] Create `backend/app/services/writing_agent/longform_tool_adapters.py`.
- [x] Move the eight longform handler functions from `tool_executor.py` into the new module.
- [x] Add local helper:

```python
def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
```

- [x] Add:

```python
def build_longform_agent_tool_adapters(
    *,
    approval_tool_metadata_provider: Callable[[dict[str, Any] | None], dict[str, dict[str, Any]]],
) -> dict[str, WritingAgentToolAdapter]:
    return {
        ...
    }
```

- [x] Ensure `execute_longform_chapter_batch` passes `approval_tool_metadata_provider=approval_tool_metadata_provider`.

### Task 4: Merge Adapter Map in Executor

- [x] In `tool_executor.py`, import:

```python
from app.services.writing_agent.longform_tool_adapters import build_longform_agent_tool_adapters
```

- [x] Replace `_STATIC_TOOL_ADAPTERS = {...}` with:

```python
def _build_static_tool_adapters() -> dict[str, WritingAgentToolAdapter]:
    adapters: dict[str, WritingAgentToolAdapter] = {
        ...
    }
    adapters.update(build_longform_agent_tool_adapters(approval_tool_metadata_provider=_approval_tool_metadata_by_name))
    return adapters


_STATIC_TOOL_ADAPTERS = _build_static_tool_adapters()
```

- [x] Remove the eight inline longform adapter entries from the base dict.

### Task 5: Verify

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py::test_longform_tool_adapters_live_in_dedicated_module -q
```

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -q
```

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -q
```

- [x] Run:

```powershell
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
docs/superpowers/notes/long-memory-agent/2026-05-23-phase174-longform-tool-adapter-module.md
```

- [x] Commit and push:

```powershell
git add backend/app/services/writing_agent/tool_adapter_types.py backend/app/services/writing_agent/longform_tool_adapters.py backend/app/services/writing_agent/tool_executor.py backend/tests/test_writing_agent_tool_executor.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase174-longform-tool-adapter-module.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase174-longform-tool-adapter-module.md
git commit -m "refactor: split longform tool adapters"
git push origin main
```
