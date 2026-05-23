# Phase177 Review Revision Tool Modules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Writing Agent 的章节审稿与修订工具从通用 registry/executor 拆到独立能力域模块。

**Architecture:** 沿用 Phase173-176 的 Agent 工具域拆分方式：`tool_registry.py` 继续作为聚合入口，`tool_executor.py` 继续作为执行入口，但审稿/修订工具的 descriptor 与 adapter 由专属模块拥有。该阶段不改变工具行为，只降低核心文件体积并强化 Agent 能力域边界。

**Tech Stack:** Python 3、pytest、Writing Agent service layer。

---

## Files

- Create: `backend/app/services/writing_agent/review_revision_tool_descriptors.py`
  - Export `REVIEW_REVISION_AGENT_TOOL_DESCRIPTORS`.
  - Own revision-only structured output schema constants currently coupled in `tool_registry.py`.
- Create: `backend/app/services/writing_agent/review_revision_tool_adapters.py`
  - Export `REVIEW_REVISION_AGENT_TOOL_ADAPTERS`.
  - Own review/revision adapter handlers and local chapter param helpers.
- Modify: `backend/app/services/writing_agent/tool_registry.py`
  - Import and spread `REVIEW_REVISION_AGENT_TOOL_DESCRIPTORS`.
  - Remove inline review/revision descriptor blocks.
- Modify: `backend/app/services/writing_agent/tool_executor.py`
  - Import and merge `REVIEW_REVISION_AGENT_TOOL_ADAPTERS`.
  - Remove inline review/revision handlers and adapter entries.
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
  - Add descriptor module boundary test.
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
  - Add adapter module boundary test.

## Success Criteria

- `tool_registry.py` no longer defines these descriptors inline:
  - `review_chapter_quality`
  - `review_chapter_continuity`
  - `plan_chapter_revision`
  - `create_revision_draft`
  - `apply_planner_revision_patch`
  - `expand_chapter_to_target`
  - `compress_chapter_to_target`
- `tool_executor.py` no longer defines the matching `_...` review/revision handlers inline.
- Existing registry behavior remains unchanged for module, category, target type, internal flag, non-blocking report behavior, sort key, schema, and availability checks.
- Existing executor metadata and dispatch tests remain green.

## Tasks

### Task 1: RED Descriptor Boundary Test

- [x] Add import in `backend/tests/test_writing_agent_tool_registry.py`:

```python
from app.services.writing_agent.review_revision_tool_descriptors import REVIEW_REVISION_AGENT_TOOL_DESCRIPTORS
```

- [x] Add:

```python
def test_review_revision_tool_descriptors_live_in_dedicated_module():
    names = [descriptor.name for descriptor in REVIEW_REVISION_AGENT_TOOL_DESCRIPTORS]

    assert names == [
        "review_chapter_quality",
        "review_chapter_continuity",
        "plan_chapter_revision",
        "create_revision_draft",
        "apply_planner_revision_patch",
        "expand_chapter_to_target",
        "compress_chapter_to_target",
    ]
    assert {descriptor.category for descriptor in REVIEW_REVISION_AGENT_TOOL_DESCRIPTORS} == {"review", "revision"}
    assert all(descriptor.internal for descriptor in REVIEW_REVISION_AGENT_TOOL_DESCRIPTORS)
    assert target_type_for_tool("plan_chapter_revision") == "revision_plan"
    assert target_type_for_tool("apply_planner_revision_patch") == "revision"
    assert "review_chapter_quality" in non_blocking_report_tool_names()
```

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_review_revision_tool_descriptors_live_in_dedicated_module -q
```

Expected: FAIL because `review_revision_tool_descriptors.py` does not exist.

### Task 2: RED Adapter Boundary Test

- [x] Add import in `backend/tests/test_writing_agent_tool_executor.py`:

```python
from app.services.writing_agent.review_revision_tool_adapters import REVIEW_REVISION_AGENT_TOOL_ADAPTERS
```

- [x] Add:

```python
def test_review_revision_tool_adapters_live_in_dedicated_module():
    names = list(REVIEW_REVISION_AGENT_TOOL_ADAPTERS)

    assert names == [
        "review_chapter_quality",
        "review_chapter_continuity",
        "plan_chapter_revision",
        "create_revision_draft",
        "apply_planner_revision_patch",
        "expand_chapter_to_target",
        "compress_chapter_to_target",
    ]
    assert {adapter.category for adapter in REVIEW_REVISION_AGENT_TOOL_ADAPTERS.values()} == {"review", "revision"}
    assert REVIEW_REVISION_AGENT_TOOL_ADAPTERS["review_chapter_quality"].mutability == "read"
    assert REVIEW_REVISION_AGENT_TOOL_ADAPTERS["create_revision_draft"].mutability == "write"
    assert (
        REVIEW_REVISION_AGENT_TOOL_ADAPTERS["apply_planner_revision_patch"].handler.__name__
        == "_apply_planner_revision_patch"
    )
```

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py::test_review_revision_tool_adapters_live_in_dedicated_module -q
```

Expected: FAIL because `review_revision_tool_adapters.py` does not exist.

### Task 3: Extract Review/Revision Descriptors

- [x] Create `backend/app/services/writing_agent/review_revision_tool_descriptors.py`.
- [x] Use `AgentToolDescriptor`, `object_schema`, and module-local `_STATUS_OUTPUT`.
- [x] Move/copy revision-only schema constants:
  - `_REVISION_PATCH_OUTPUT`
  - `_CHAPTER_EXPANSION_OUTPUT`
  - `_CHAPTER_COMPRESSION_OUTPUT`
- [x] Move the seven review/revision descriptor blocks into `REVIEW_REVISION_AGENT_TOOL_DESCRIPTORS`.
- [x] In `tool_registry.py`, import and spread:

```python
from app.services.writing_agent.review_revision_tool_descriptors import REVIEW_REVISION_AGENT_TOOL_DESCRIPTORS

...
    *REVIEW_REVISION_AGENT_TOOL_DESCRIPTORS,
```

- [x] Remove inline descriptor blocks and now-unused schema constants from `tool_registry.py`.

### Task 4: Extract Review/Revision Adapters

- [x] Create `backend/app/services/writing_agent/review_revision_tool_adapters.py`.
- [x] Move review/revision adapter handlers from `tool_executor.py`.
- [x] Add local helpers:

```python
def _chapter_index(tool: WritingAgentToolRequest) -> int:
    return int(tool.params.get("chapter_index") or 1)


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
```

- [x] Export `REVIEW_REVISION_AGENT_TOOL_ADAPTERS` with the seven matching adapter entries.
- [x] In `tool_executor.py`, import and merge:

```python
from app.services.writing_agent.review_revision_tool_adapters import REVIEW_REVISION_AGENT_TOOL_ADAPTERS

...
_STATIC_TOOL_ADAPTERS.update(REVIEW_REVISION_AGENT_TOOL_ADAPTERS)
```

- [x] Remove inline review/revision handlers and adapter entries from `tool_executor.py`.

### Task 5: Verification

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_review_revision_tool_descriptors_live_in_dedicated_module -q
pytest backend/tests/test_writing_agent_tool_executor.py::test_review_revision_tool_adapters_live_in_dedicated_module -q
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
docs/superpowers/notes/long-memory-agent/2026-05-23-phase177-review-revision-tool-modules.md
```

- [x] Commit and push:

```powershell
git add backend/app/services/writing_agent/review_revision_tool_descriptors.py backend/app/services/writing_agent/review_revision_tool_adapters.py backend/app/services/writing_agent/tool_registry.py backend/app/services/writing_agent/tool_executor.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase177-review-revision-tool-modules.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase177-review-revision-tool-modules.md
git commit -m "refactor: split review revision agent tools"
git push origin main
```
