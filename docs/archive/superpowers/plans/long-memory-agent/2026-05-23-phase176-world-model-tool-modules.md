# Phase176 World Model Tool Modules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Athena/世界模型相关 Writing Agent 工具的 descriptor 和 static adapter 从通用 registry/executor 拆到世界模型能力域模块。

**Architecture:** 复用 Phase173-175 建立的能力域拆分模式：`tool_registry.py` 只聚合 descriptor 模块，`tool_executor.py` 只聚合 adapter 模块。新增 `world_model_tool_descriptors.py` 与 `world_model_tool_adapters.py`，承载世界模型导入、章节分析、提案审阅/处理和连续性锚点种子工具。

**Tech Stack:** Python 3、pytest、Writing Agent service layer。

---

## Files

- Create: `backend/app/services/writing_agent/world_model_tool_descriptors.py`
  - Export `WORLD_MODEL_AGENT_TOOL_DESCRIPTORS`.
  - Own local structured output schema constants that are only used by this domain.
- Create: `backend/app/services/writing_agent/world_model_tool_adapters.py`
  - Export `WORLD_MODEL_AGENT_TOOL_ADAPTERS`.
  - Own world-model adapter handlers and local param parsing helper.
- Modify: `backend/app/services/writing_agent/tool_registry.py`
  - Import and spread `WORLD_MODEL_AGENT_TOOL_DESCRIPTORS`.
  - Remove inline world-model descriptor blocks.
- Modify: `backend/app/services/writing_agent/tool_executor.py`
  - Import and merge `WORLD_MODEL_AGENT_TOOL_ADAPTERS`.
  - Remove inline world-model handlers and adapter entries.
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
  - Add descriptor module boundary test.
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
  - Add adapter module boundary test.

## Success Criteria

- `tool_registry.py` no longer defines these descriptors inline:
  - `import_setup_world_model`
  - `analyze_chapter_world_model`
  - `review_world_model_proposals`
  - `inspect_agent_world_model_route`
  - `plan_world_model_proposal_resolution`
  - `preview_world_model_proposal_resolution`
  - `apply_world_model_proposal_resolution`
  - `draft_world_model_proposal_resolution_decisions`
  - `draft_high_value_world_proposal_resolution_decisions`
  - `seed_continuity_anchor_proposals`
- `tool_executor.py` no longer defines the matching `_...` world-model handlers inline.
- Existing registry behavior remains unchanged for target type, category, internal flag, non-blocking report behavior, and availability checks.
- Existing executor metadata and dispatch tests remain green.

## Tasks

### Task 1: RED Descriptor Boundary Test

- [x] Add import in `backend/tests/test_writing_agent_tool_registry.py`:

```python
from app.services.writing_agent.world_model_tool_descriptors import WORLD_MODEL_AGENT_TOOL_DESCRIPTORS
```

- [x] Add:

```python
def test_world_model_tool_descriptors_live_in_dedicated_module():
    names = [descriptor.name for descriptor in WORLD_MODEL_AGENT_TOOL_DESCRIPTORS]

    assert names == [
        "import_setup_world_model",
        "analyze_chapter_world_model",
        "review_world_model_proposals",
        "inspect_agent_world_model_route",
        "plan_world_model_proposal_resolution",
        "preview_world_model_proposal_resolution",
        "apply_world_model_proposal_resolution",
        "draft_world_model_proposal_resolution_decisions",
        "draft_high_value_world_proposal_resolution_decisions",
        "seed_continuity_anchor_proposals",
    ]
    assert {descriptor.category for descriptor in WORLD_MODEL_AGENT_TOOL_DESCRIPTORS} == {
        "athena_world_model",
        "maintenance",
    }
    assert all(descriptor.internal for descriptor in WORLD_MODEL_AGENT_TOOL_DESCRIPTORS)
    assert target_type_for_tool("inspect_agent_world_model_route") == "agent_world_model_route"
    assert target_type_for_tool("apply_world_model_proposal_resolution") == "world_model"
```

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_world_model_tool_descriptors_live_in_dedicated_module -q
```

Expected: FAIL because `world_model_tool_descriptors.py` does not exist.

### Task 2: RED Adapter Boundary Test

- [x] Add import in `backend/tests/test_writing_agent_tool_executor.py`:

```python
from app.services.writing_agent.world_model_tool_adapters import WORLD_MODEL_AGENT_TOOL_ADAPTERS
```

- [x] Add:

```python
def test_world_model_tool_adapters_live_in_dedicated_module():
    names = list(WORLD_MODEL_AGENT_TOOL_ADAPTERS)

    assert names == [
        "import_setup_world_model",
        "analyze_chapter_world_model",
        "review_world_model_proposals",
        "inspect_agent_world_model_route",
        "plan_world_model_proposal_resolution",
        "preview_world_model_proposal_resolution",
        "apply_world_model_proposal_resolution",
        "draft_world_model_proposal_resolution_decisions",
        "draft_high_value_world_proposal_resolution_decisions",
        "seed_continuity_anchor_proposals",
    ]
    assert WORLD_MODEL_AGENT_TOOL_ADAPTERS["inspect_agent_world_model_route"].mutability == "read"
    assert WORLD_MODEL_AGENT_TOOL_ADAPTERS["apply_world_model_proposal_resolution"].mutability == "write"
    assert (
        WORLD_MODEL_AGENT_TOOL_ADAPTERS["apply_world_model_proposal_resolution"].handler.__name__
        == "_apply_world_model_proposal_resolution"
    )
```

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py::test_world_model_tool_adapters_live_in_dedicated_module -q
```

Expected: FAIL because `world_model_tool_adapters.py` does not exist.

### Task 3: Extract World Model Descriptors

- [x] Create `backend/app/services/writing_agent/world_model_tool_descriptors.py`.
- [x] Use `AgentToolDescriptor` and `object_schema`.
- [x] Move/copy world-model-only schema constants:
  - `_SETUP_WORLD_MODEL_IMPORT_OUTPUT`
  - `_CONTINUITY_ANCHOR_SEED_OUTPUT`
- [x] Move the ten world-model descriptor blocks into `WORLD_MODEL_AGENT_TOOL_DESCRIPTORS`.
- [x] In `tool_registry.py`, import and spread:

```python
from app.services.writing_agent.world_model_tool_descriptors import WORLD_MODEL_AGENT_TOOL_DESCRIPTORS

...
    *WORLD_MODEL_AGENT_TOOL_DESCRIPTORS,
```

- [x] Remove inline descriptor blocks and now-unused schema constants from `tool_registry.py`.

### Task 4: Extract World Model Adapters

- [x] Create `backend/app/services/writing_agent/world_model_tool_adapters.py`.
- [x] Move world-model adapter handlers from `tool_executor.py`.
- [x] Add local `_optional_int()` helper.
- [x] Export `WORLD_MODEL_AGENT_TOOL_ADAPTERS` with the ten matching adapter entries.
- [x] In `tool_executor.py`, import and merge:

```python
from app.services.writing_agent.world_model_tool_adapters import WORLD_MODEL_AGENT_TOOL_ADAPTERS

...
_STATIC_TOOL_ADAPTERS.update(WORLD_MODEL_AGENT_TOOL_ADAPTERS)
```

- [x] Remove inline world-model handlers and adapter entries from `tool_executor.py`.

### Task 5: Verification

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_world_model_tool_descriptors_live_in_dedicated_module -q
pytest backend/tests/test_writing_agent_tool_executor.py::test_world_model_tool_adapters_live_in_dedicated_module -q
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
docs/superpowers/notes/long-memory-agent/2026-05-23-phase176-world-model-tool-modules.md
```

- [x] Commit and push:

```powershell
git add backend/app/services/writing_agent/world_model_tool_descriptors.py backend/app/services/writing_agent/world_model_tool_adapters.py backend/app/services/writing_agent/tool_registry.py backend/app/services/writing_agent/tool_executor.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase176-world-model-tool-modules.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase176-world-model-tool-modules.md
git commit -m "refactor: split world model agent tools"
git push origin main
```
