# Phase183 Tool Aggregation Boundary Guards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 增加聚合层边界守护，防止 `tool_registry.py` / `tool_executor.py` 后续重新内联 descriptor 或 adapter 构造。

**Architecture:** 新增一个轻量静态边界测试文件，读取聚合层源码并禁止 constructor/import 泄漏。最小实现是移除聚合文件中只为类型标注保留的构造类型运行时 import，让聚合层只依赖已拆分模块导出的常量/builder。

**Tech Stack:** Python 3、pytest、Writing Agent service layer。

---

## Files

- Create: `backend/tests/test_writing_agent_tool_aggregation_boundaries.py`
  - Assert `tool_registry.py` does not import or construct `AgentToolDescriptor`.
  - Assert `tool_registry.py` does not import or call `object_schema`.
  - Assert `tool_executor.py` does not import or construct `WritingAgentToolAdapter`.
  - Assert consumers import `AgentToolDescriptor` / `WritingAgentToolContext` from their source modules, not aggregation modules.
- Modify: `backend/app/services/writing_agent/tool_registry.py`
  - Remove runtime `AgentToolDescriptor` import.
  - Use `Any` for local aggregation annotations.
- Modify: `backend/app/services/writing_agent/tool_executor.py`
  - Remove runtime `WritingAgentToolAdapter`, `WritingAgentToolContext`, and `PreflightWriting` imports.
  - Use `Any` for local aggregation/context annotations while retaining `WritingAgentToolExecutionResult`.
- Modify: `backend/app/services/writing_agent/tool_contracts.py`
  - Import `AgentToolDescriptor` from `tool_descriptor_types`, not `tool_registry`.
- Modify: `backend/app/services/writing_agent/write_gate_coverage.py`
  - Import `AgentToolDescriptor` from `tool_descriptor_types`, not `tool_registry`.
- Modify: `backend/app/services/writing_agent/run_service.py`
  - Import `WritingAgentToolContext` from `tool_adapter_types`, not `tool_executor`.
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
  - Import `WritingAgentToolContext` from `tool_adapter_types`, not `tool_executor`.

## Success Criteria

- Boundary tests fail before implementation because current files still import constructor types.
- Boundary tests pass after implementation.
- Existing registry/executor behavior remains unchanged.
- `tool_registry.py` remains descriptor aggregation + availability diagnostics.
- `tool_executor.py` remains adapter aggregation + execution dispatch.

## Non-Scope

- Do not change any tool descriptor schema.
- Do not change adapter dispatch order or mutability.
- Do not add legacy Hermes static adapters.

## Tasks

### Task 1: RED Boundary Tests

- [x] Create `backend/tests/test_writing_agent_tool_aggregation_boundaries.py`:

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _source(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_tool_registry_remains_descriptor_aggregator_only():
    source = _source("app/services/writing_agent/tool_registry.py")

    assert "AgentToolDescriptor(" not in source
    assert "from app.services.writing_agent.tool_descriptor_types import AgentToolDescriptor" not in source
    assert "object_schema" not in source


def test_tool_executor_remains_adapter_aggregator_only():
    source = _source("app/services/writing_agent/tool_executor.py")

    assert "WritingAgentToolAdapter" not in source
```

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_aggregation_boundaries.py -q
```

Expected: FAIL because `tool_registry.py` still imports `AgentToolDescriptor` and `tool_executor.py` still imports/annotates `WritingAgentToolAdapter`.

### Task 2: Remove Runtime Constructor Type Imports

- [x] In `backend/app/services/writing_agent/tool_registry.py`, remove:

```python
from app.services.writing_agent.tool_descriptor_types import AgentToolDescriptor
```

- [x] Change annotations:

```python
_TOOL_DESCRIPTORS: tuple[Any, ...] = (
...
def list_agent_tool_descriptors() -> tuple[Any, ...]:
...
def get_agent_tool_descriptor(name: str) -> Any | None:
...
def _diagnostics_for_descriptor(descriptor: Any, state: _ProjectToolState) -> list[dict[str, Any]]:
```

- [x] In `backend/app/services/writing_agent/tool_executor.py`, replace the runtime import block with:

```python
from app.services.writing_agent.tool_adapter_types import WritingAgentToolExecutionResult
```

- [x] Change annotations:

```python
async def execute_writing_agent_tool(
    context: Any,
    tool: WritingAgentToolRequest,
    *,
    preflight_writing: Any | None = None,
) -> WritingAgentToolExecutionResult:
...
_STATIC_TOOL_ADAPTERS: dict[str, Any] = dict(AGENT_TASK_QUEUE_TOOL_ADAPTERS)
```

### Task 3: Verification

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_aggregation_boundaries.py -q
pytest backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py -q
python -m compileall backend/app/services/writing_agent
```

### Task 4: Report, Hygiene, Commit, Push

- [x] Run:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

- [x] Write report:

```text
docs/superpowers/notes/long-memory-agent/2026-05-23-phase183-tool-aggregation-boundary-guards.md
```

- [x] Commit and push:

```powershell
git add backend/app/services/writing_agent/tool_registry.py backend/app/services/writing_agent/tool_executor.py backend/tests/test_writing_agent_tool_aggregation_boundaries.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase183-tool-aggregation-boundary-guards.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase183-tool-aggregation-boundary-guards.md
git commit -m "test: guard writing agent tool aggregation boundaries"
git push origin main
```
