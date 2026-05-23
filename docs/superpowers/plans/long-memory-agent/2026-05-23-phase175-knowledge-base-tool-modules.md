# Phase175 Knowledge Base Tool Modules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Writing Agent 知识库工具的 descriptor 和 static adapter 从通用 registry/executor 拆到知识库能力域模块，为后续长期记忆 Agent 的知识库扩展留出清晰边界。

**Architecture:** 复用 Phase173/174 新增的 `tool_descriptor_types.py` 和 `tool_adapter_types.py`。新增 `knowledge_base_tool_descriptors.py` 与 `knowledge_base_tool_adapters.py`，通用 `tool_registry.py` 与 `tool_executor.py` 只聚合这些能力域模块。

**Tech Stack:** Python 3、pytest、Writing Agent service layer。

---

## Files

- Create: `backend/app/services/writing_agent/knowledge_base_tool_descriptors.py`
  - Export `KNOWLEDGE_BASE_AGENT_TOOL_DESCRIPTORS`.
- Create: `backend/app/services/writing_agent/knowledge_base_tool_adapters.py`
  - Export `KNOWLEDGE_BASE_AGENT_TOOL_ADAPTERS`.
- Modify: `backend/app/services/writing_agent/tool_registry.py`
  - Import and spread knowledge base descriptors.
  - Remove inline knowledge base descriptor blocks.
- Modify: `backend/app/services/writing_agent/tool_executor.py`
  - Import and merge knowledge base adapters.
  - Remove inline knowledge base handlers and adapter entries.
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
  - Assert knowledge base descriptors live in the dedicated module.
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
  - Assert knowledge base adapters live in the dedicated module.

## Success Criteria

- `tool_registry.py` no longer defines `inspect_agent_knowledge_base_route` or `record_agent_knowledge_base_candidate` inline.
- `tool_executor.py` no longer defines `_inspect_agent_knowledge_base_route` or `_record_agent_knowledge_base_candidate` inline.
- Registry functions still expose both tools with the same category, target type, and non-blocking behavior.
- Executor metadata and dispatch tests remain green.
- Existing public imports from `tool_registry.py` and `tool_executor.py` remain stable.

## Tasks

### Task 1: Write Failing Descriptor Boundary Test

- [x] In `backend/tests/test_writing_agent_tool_registry.py`, add:

```python
from app.services.writing_agent.knowledge_base_tool_descriptors import KNOWLEDGE_BASE_AGENT_TOOL_DESCRIPTORS
```

- [x] Add:

```python
def test_knowledge_base_tool_descriptors_live_in_dedicated_module():
    names = [descriptor.name for descriptor in KNOWLEDGE_BASE_AGENT_TOOL_DESCRIPTORS]

    assert names == [
        "inspect_agent_knowledge_base_route",
        "record_agent_knowledge_base_candidate",
    ]
    assert {descriptor.category for descriptor in KNOWLEDGE_BASE_AGENT_TOOL_DESCRIPTORS} == {"knowledge_base"}
    assert {descriptor.module for descriptor in KNOWLEDGE_BASE_AGENT_TOOL_DESCRIPTORS} == {"writing_agent"}
    assert all(descriptor.internal for descriptor in KNOWLEDGE_BASE_AGENT_TOOL_DESCRIPTORS)
    assert target_type_for_tool("inspect_agent_knowledge_base_route") == "agent_knowledge_base_route"
```

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_knowledge_base_tool_descriptors_live_in_dedicated_module -q
```

Expected: FAIL because the module does not exist.

### Task 2: Write Failing Adapter Boundary Test

- [x] In `backend/tests/test_writing_agent_tool_executor.py`, add:

```python
from app.services.writing_agent.knowledge_base_tool_adapters import KNOWLEDGE_BASE_AGENT_TOOL_ADAPTERS
```

- [x] Add:

```python
def test_knowledge_base_tool_adapters_live_in_dedicated_module():
    names = list(KNOWLEDGE_BASE_AGENT_TOOL_ADAPTERS)

    assert names == [
        "inspect_agent_knowledge_base_route",
        "record_agent_knowledge_base_candidate",
    ]
    assert {adapter.category for adapter in KNOWLEDGE_BASE_AGENT_TOOL_ADAPTERS.values()} == {"knowledge_base"}
    assert KNOWLEDGE_BASE_AGENT_TOOL_ADAPTERS["inspect_agent_knowledge_base_route"].mutability == "read"
    assert KNOWLEDGE_BASE_AGENT_TOOL_ADAPTERS["record_agent_knowledge_base_candidate"].mutability == "write"
    assert (
        KNOWLEDGE_BASE_AGENT_TOOL_ADAPTERS["record_agent_knowledge_base_candidate"].handler.__name__
        == "_record_agent_knowledge_base_candidate"
    )
```

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py::test_knowledge_base_tool_adapters_live_in_dedicated_module -q
```

Expected: FAIL because the module does not exist.

### Task 3: Extract Knowledge Base Descriptors

- [x] Create `knowledge_base_tool_descriptors.py` using `AgentToolDescriptor` and `object_schema`.
- [x] Move the two knowledge base descriptor blocks from `tool_registry.py`.
- [x] In `_TOOL_DESCRIPTORS`, add:

```python
    *KNOWLEDGE_BASE_AGENT_TOOL_DESCRIPTORS,
```

- [x] Delete inline descriptor blocks from `tool_registry.py`.

### Task 4: Extract Knowledge Base Adapters

- [x] Create `knowledge_base_tool_adapters.py`.
- [x] Move `_inspect_agent_knowledge_base_route` and `_record_agent_knowledge_base_candidate`.
- [x] Add local helpers `_optional_int()`, `_optional_float()`, `_string_list()` as needed.
- [x] Export:

```python
KNOWLEDGE_BASE_AGENT_TOOL_ADAPTERS: dict[str, WritingAgentToolAdapter] = {
    ...
}
```

- [x] In `tool_executor.py`, import and merge:

```python
_STATIC_TOOL_ADAPTERS.update(KNOWLEDGE_BASE_AGENT_TOOL_ADAPTERS)
```

- [x] Delete inline handler functions and adapter entries from `tool_executor.py`.

### Task 5: Verify

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_knowledge_base_tool_descriptors_live_in_dedicated_module -q
pytest backend/tests/test_writing_agent_tool_executor.py::test_knowledge_base_tool_adapters_live_in_dedicated_module -q
```

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -q
pytest backend/tests/test_writing_agent_tool_executor.py -q
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
docs/superpowers/notes/long-memory-agent/2026-05-23-phase175-knowledge-base-tool-modules.md
```

- [x] Commit and push:

```powershell
git add backend/app/services/writing_agent/knowledge_base_tool_descriptors.py backend/app/services/writing_agent/knowledge_base_tool_adapters.py backend/app/services/writing_agent/tool_registry.py backend/app/services/writing_agent/tool_executor.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase175-knowledge-base-tool-modules.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase175-knowledge-base-tool-modules.md
git commit -m "refactor: split knowledge base agent tools"
git push origin main
```
