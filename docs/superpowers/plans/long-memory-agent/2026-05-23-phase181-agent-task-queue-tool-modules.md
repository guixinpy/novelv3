# Phase181 Agent Task Queue Tool Modules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Writing Agent 剩余内联 task queue / job projection 工具拆成独立能力域模块。

**Architecture:** 新增 `agent_task_queue_tool_descriptors.py` 和 `agent_task_queue_tool_adapters.py`，只承载 Agent 任务队列投影与章节冲突恢复计划工具。`tool_registry.py` 和 `tool_executor.py` 继续作为聚合层，保留 legacy Hermes action descriptors 和 injected `preflight_writing` special-case。

**Tech Stack:** Python 3、pytest、Writing Agent service layer。

---

## Files

- Create: `backend/app/services/writing_agent/agent_task_queue_tool_descriptors.py`
  - Export `AGENT_TASK_QUEUE_TOOL_DESCRIPTORS`.
  - Own task queue projection output schema constants.
- Create: `backend/app/services/writing_agent/agent_task_queue_tool_adapters.py`
  - Export `AGENT_TASK_QUEUE_TOOL_ADAPTERS`.
  - Own adapter handlers for task queue projection tools.
- Modify: `backend/app/services/writing_agent/tool_registry.py`
  - Import and spread `AGENT_TASK_QUEUE_TOOL_DESCRIPTORS`.
  - Remove inline descriptor blocks for scoped tools.
- Modify: `backend/app/services/writing_agent/tool_executor.py`
  - Import and merge `AGENT_TASK_QUEUE_TOOL_ADAPTERS`.
  - Remove inline handlers and adapter entries for scoped tools.
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
  - Add descriptor module boundary test.
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
  - Add adapter module boundary test.

## Success Criteria

- `tool_registry.py` no longer defines these descriptors inline:
  - `inspect_agent_job_projection`
  - `plan_chapter_conflict_recovery`
- `tool_executor.py` no longer defines matching handlers or adapter entries inline.
- Existing dispatch behavior is unchanged:
  - `inspect_agent_job_projection` trims string filters and coerces `limit` / `chapter_index`.
  - `plan_chapter_conflict_recovery` coerces `chapter_index`.
- Both tools remain internal, read-only adapters, category `task_queue`, and non-blocking report tools.

## Non-Scope

- Do not move `generate_setup`, `generate_storyline`, or `generate_outline`; they are legacy action-backed descriptors.
- Do not merge these two tools into `longform_tool_*`; they are Agent job projection/recovery planning, not longform batch execution.
- Do not change queue semantics, recovery recommendations, or write behavior.

## Tasks

### Task 1: RED Descriptor Boundary Test

- [x] Add import in `backend/tests/test_writing_agent_tool_registry.py`:

```python
from app.services.writing_agent.agent_task_queue_tool_descriptors import AGENT_TASK_QUEUE_TOOL_DESCRIPTORS
```

- [x] Add:

```python
def test_agent_task_queue_tool_descriptors_live_in_dedicated_module():
    names = [descriptor.name for descriptor in AGENT_TASK_QUEUE_TOOL_DESCRIPTORS]

    assert names == [
        "inspect_agent_job_projection",
        "plan_chapter_conflict_recovery",
    ]
    assert {descriptor.category for descriptor in AGENT_TASK_QUEUE_TOOL_DESCRIPTORS} == {"task_queue"}
    assert {descriptor.module for descriptor in AGENT_TASK_QUEUE_TOOL_DESCRIPTORS} == {"writing_agent"}
    assert all(descriptor.internal for descriptor in AGENT_TASK_QUEUE_TOOL_DESCRIPTORS)
    assert all(descriptor.non_blocking_report for descriptor in AGENT_TASK_QUEUE_TOOL_DESCRIPTORS)
    assert target_type_for_tool("inspect_agent_job_projection") == "agent_job_projection"
    assert target_type_for_tool("plan_chapter_conflict_recovery") == "agent_tool_plan"
```

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_agent_task_queue_tool_descriptors_live_in_dedicated_module -q
```

Expected: FAIL because `agent_task_queue_tool_descriptors.py` does not exist.

### Task 2: RED Adapter Boundary Test

- [x] Add import in `backend/tests/test_writing_agent_tool_executor.py`:

```python
from app.services.writing_agent.agent_task_queue_tool_adapters import AGENT_TASK_QUEUE_TOOL_ADAPTERS
```

- [x] Add:

```python
def test_agent_task_queue_tool_adapters_live_in_dedicated_module():
    names = list(AGENT_TASK_QUEUE_TOOL_ADAPTERS)

    assert names == [
        "plan_chapter_conflict_recovery",
        "inspect_agent_job_projection",
    ]
    assert {adapter.category for adapter in AGENT_TASK_QUEUE_TOOL_ADAPTERS.values()} == {"task_queue"}
    assert {adapter.mutability for adapter in AGENT_TASK_QUEUE_TOOL_ADAPTERS.values()} == {"read"}
    assert (
        AGENT_TASK_QUEUE_TOOL_ADAPTERS["plan_chapter_conflict_recovery"].handler.__name__
        == "_plan_chapter_conflict_recovery"
    )
    assert (
        AGENT_TASK_QUEUE_TOOL_ADAPTERS["inspect_agent_job_projection"].handler.__name__
        == "_inspect_agent_job_projection"
    )
```

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py::test_agent_task_queue_tool_adapters_live_in_dedicated_module -q
```

Expected: FAIL because `agent_task_queue_tool_adapters.py` does not exist.

### Task 3: Extract Task Queue Descriptors

- [x] Create `backend/app/services/writing_agent/agent_task_queue_tool_descriptors.py`.
- [x] Move the two descriptor blocks into `AGENT_TASK_QUEUE_TOOL_DESCRIPTORS`.
- [x] In `tool_registry.py`, import and spread:

```python
from app.services.writing_agent.agent_task_queue_tool_descriptors import AGENT_TASK_QUEUE_TOOL_DESCRIPTORS

...
    *AGENT_TASK_QUEUE_TOOL_DESCRIPTORS,
```

- [x] Remove inline descriptor blocks from `tool_registry.py`.

### Task 4: Extract Task Queue Adapters

- [x] Create `backend/app/services/writing_agent/agent_task_queue_tool_adapters.py`.
- [x] Move the two adapter handlers from `tool_executor.py`.
- [x] Export:

```python
AGENT_TASK_QUEUE_TOOL_ADAPTERS: dict[str, WritingAgentToolAdapter] = {
    ...
}
```

- [x] In `tool_executor.py`, import and merge:

```python
from app.services.writing_agent.agent_task_queue_tool_adapters import AGENT_TASK_QUEUE_TOOL_ADAPTERS

...
_STATIC_TOOL_ADAPTERS.update(AGENT_TASK_QUEUE_TOOL_ADAPTERS)
```

- [x] Remove inline handlers and adapter entries from `tool_executor.py`.

### Task 5: Verification

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_agent_task_queue_tool_descriptors_live_in_dedicated_module -q
pytest backend/tests/test_writing_agent_tool_executor.py::test_agent_task_queue_tool_adapters_live_in_dedicated_module -q
```

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py -q
pytest backend/tests/test_writing_agent_tool_executor.py -k "agent_task_queue or inspect_agent_job_projection or plan_chapter_conflict_recovery" -q
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
docs/superpowers/notes/long-memory-agent/2026-05-23-phase181-agent-task-queue-tool-modules.md
```

- [x] Commit and push:

```powershell
git add backend/app/services/writing_agent/agent_task_queue_tool_descriptors.py backend/app/services/writing_agent/agent_task_queue_tool_adapters.py backend/app/services/writing_agent/tool_registry.py backend/app/services/writing_agent/tool_executor.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase181-agent-task-queue-tool-modules.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase181-agent-task-queue-tool-modules.md
git commit -m "refactor: split agent task queue tools"
git push origin main
```
