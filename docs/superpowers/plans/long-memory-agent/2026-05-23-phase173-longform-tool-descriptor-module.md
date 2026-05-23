# Phase173 Longform Tool Descriptor Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将后端长篇批次 Agent tool descriptor 从通用 `tool_registry.py` 拆到独立模块，降低后续 Agent 工具继续扩展时的 registry 膨胀风险。

**Architecture:** 参考 `references/agent-projects/hermes-agent/AGENTS.md` 中“工具实现按文件拆分、中央 registry 负责收集和暴露”的组织原则，但不照搬其插件注册机制。本阶段只做 descriptor 边界拆分：新增 descriptor 类型 helper 模块和 longform descriptor 模块，`tool_registry.py` 继续作为公开 registry API。

**Tech Stack:** Python 3、FastAPI service layer、pytest。

---

## Files

- Create: `backend/app/services/writing_agent/tool_descriptor_types.py`
  - Own `AgentToolDescriptor`.
  - Own public `object_schema()` helper.
- Create: `backend/app/services/writing_agent/longform_tool_descriptors.py`
  - Export `LONGFORM_AGENT_TOOL_DESCRIPTORS`.
  - Own the eight longform batch descriptors:
    - `plan_longform_chapter_batch`
    - `enqueue_longform_chapter_batch`
    - `inspect_longform_chapter_batch`
    - `execute_longform_chapter_batch_preflight`
    - `prepare_longform_chapter_batch_execution`
    - `execute_longform_chapter_batch`
    - `review_longform_chapter_batch_execution`
    - `route_longform_chapter_batch_after_review`
- Modify: `backend/app/services/writing_agent/tool_registry.py`
  - Import `AgentToolDescriptor` and `object_schema`.
  - Import and spread `LONGFORM_AGENT_TOOL_DESCRIPTORS` into `_TOOL_DESCRIPTORS`.
  - Remove inline longform descriptor definitions.
  - Keep public imports stable for existing modules that import `AgentToolDescriptor` from `tool_registry.py`.
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
  - Assert the dedicated longform descriptor module exports the expected names and schema basics.

## Success Criteria

- `tool_registry.py` no longer defines the eight longform batch descriptors inline.
- `longform_tool_descriptors.py` owns the longform descriptor contracts.
- Public registry behavior remains unchanged:
  - `allowed_tool_names()`
  - `target_type_for_tool()`
  - `non_blocking_report_tool_names()`
  - `list_agent_tool_descriptors()`
- Existing imports of `AgentToolDescriptor` from `tool_registry.py` still work.
- Tool executor tests still see all longform tools as handled static adapters.

## Tasks

### Task 1: Write Failing Module Boundary Test

- [x] In `backend/tests/test_writing_agent_tool_registry.py`, add:

```python
from app.services.writing_agent.longform_tool_descriptors import LONGFORM_AGENT_TOOL_DESCRIPTORS
```

- [x] Add this test:

```python
def test_longform_tool_descriptors_live_in_dedicated_module():
    names = [descriptor.name for descriptor in LONGFORM_AGENT_TOOL_DESCRIPTORS]

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
    assert {descriptor.category for descriptor in LONGFORM_AGENT_TOOL_DESCRIPTORS} == {"task_queue"}
    assert {descriptor.module for descriptor in LONGFORM_AGENT_TOOL_DESCRIPTORS} == {"writing_agent"}
    assert all(descriptor.internal for descriptor in LONGFORM_AGENT_TOOL_DESCRIPTORS)
    assert target_type_for_tool("execute_longform_chapter_batch") == "background_task"
```

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_longform_tool_descriptors_live_in_dedicated_module -q
```

Expected: FAIL because `app.services.writing_agent.longform_tool_descriptors` does not exist yet.

### Task 2: Extract Shared Descriptor Types

- [x] Create `backend/app/services/writing_agent/tool_descriptor_types.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AgentToolDescriptor:
    name: str
    module: str
    category: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    target_type: str | None
    internal: bool = False
    non_blocking_report: bool = False
    sort_key: int = 100
    availability_checks: tuple[str, ...] = ()
    warning_checks: tuple[str, ...] = ()

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "module": self.module,
            "category": self.category,
            "description": self.description,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "target_type": self.target_type,
            "internal": self.internal,
            "non_blocking_report": self.non_blocking_report,
        }


def object_schema(properties: dict[str, Any] | None = None, required: tuple[str, ...] = ()) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "object", "properties": properties or {}, "additionalProperties": True}
    if required:
        schema["required"] = list(required)
    return schema
```

- [x] In `tool_registry.py`, replace the inline `AgentToolDescriptor` and `_object_schema()` definitions with:

```python
from app.services.writing_agent.tool_descriptor_types import AgentToolDescriptor
from app.services.writing_agent.tool_descriptor_types import object_schema as _object_schema
```

- [x] Keep `from dataclasses import dataclass` in `tool_registry.py` because `_ProjectToolState` still uses it.

### Task 3: Extract Longform Descriptors

- [x] Create `backend/app/services/writing_agent/longform_tool_descriptors.py`.
- [x] Move the eight longform `AgentToolDescriptor(...)` blocks from `tool_registry.py` into:

```python
from __future__ import annotations

from app.services.writing_agent.tool_descriptor_types import AgentToolDescriptor, object_schema


LONGFORM_AGENT_TOOL_DESCRIPTORS: tuple[AgentToolDescriptor, ...] = (
    ...
)
```

- [x] In `tool_registry.py`, import:

```python
from app.services.writing_agent.longform_tool_descriptors import LONGFORM_AGENT_TOOL_DESCRIPTORS
```

- [x] In `_TOOL_DESCRIPTORS`, add:

```python
    *LONGFORM_AGENT_TOOL_DESCRIPTORS,
```

immediately after `inspect_agent_intent_projection`.

- [x] Delete the eight inline longform descriptor blocks from `tool_registry.py`.

### Task 4: Verify Registry Behavior

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -q
```

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -q
```

- [x] Run:

```powershell
python -m compileall backend/app/services/writing_agent
```

### Task 5: Report, Hygiene, Commit, Push

- [x] Run:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

- [x] Write report:

```text
docs/superpowers/notes/long-memory-agent/2026-05-23-phase173-longform-tool-descriptor-module.md
```

- [x] Commit and push:

```powershell
git add backend/app/services/writing_agent/tool_descriptor_types.py backend/app/services/writing_agent/longform_tool_descriptors.py backend/app/services/writing_agent/tool_registry.py backend/tests/test_writing_agent_tool_registry.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase173-longform-tool-descriptor-module.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase173-longform-tool-descriptor-module.md
git commit -m "refactor: split longform tool descriptors"
git push origin main
```
