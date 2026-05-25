# Phase180 Agent Generation Tool Modules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Writing Agent 的 Agent-native generation / outline maintenance 工具拆成独立能力域模块。

**Architecture:** 新增 `agent_generation_tool_descriptors.py` 和 `agent_generation_tool_adapters.py`，承载章节生成、生成审批、outline window 扩展和 outline gap 回填工具。`tool_executor.py` 通过 builder 注入 `approval_tool_metadata_provider`，避免新模块反向依赖 executor 全局 adapter metadata。

**Tech Stack:** Python 3、pytest、Writing Agent service layer。

---

## Files

- Create: `backend/app/services/writing_agent/agent_generation_tool_descriptors.py`
  - Export `AGENT_GENERATION_TOOL_DESCRIPTORS`.
  - Own generation / outline maintenance output schema constants.
- Create: `backend/app/services/writing_agent/agent_generation_tool_adapters.py`
  - Export `build_agent_generation_tool_adapters(...)`.
  - Own adapter handlers for generation and outline maintenance tools.
- Modify: `backend/app/services/writing_agent/tool_registry.py`
  - Import and spread `AGENT_GENERATION_TOOL_DESCRIPTORS`.
  - Remove inline descriptor blocks for the scoped tools.
- Modify: `backend/app/services/writing_agent/tool_executor.py`
  - Import and merge `build_agent_generation_tool_adapters(...)`.
  - Remove inline handlers and adapter entries for the scoped tools.
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
  - Add descriptor module boundary test.
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
  - Add adapter module boundary test.

## Success Criteria

- `tool_registry.py` no longer defines these descriptors inline:
  - `expand_outline_window`
  - `generate_chapter`
  - `prepare_generate_chapter_execution`
  - `execute_generate_chapter_with_approval`
  - `backfill_outline_gaps`
- `tool_executor.py` no longer defines matching handlers inline.
- `execute_generate_chapter_with_approval` still receives current approval tool metadata through a provider.
- Existing direct generation approval and outline/backfill tests remain green.

## Non-Scope

- Do not move `generate_setup`, `generate_storyline`, or `generate_outline` in this phase. They are legacy action-backed descriptors without static Agent-native adapters, and should be split with legacy/Hermes action migration separately.
- Do not move task queue tools (`inspect_agent_job_projection`, `plan_chapter_conflict_recovery`).
- Do not move review, world model, longform batch, memory/trace, or knowledge base tools.

## Tasks

### Task 1: RED Descriptor Boundary Test

- [x] Add import in `backend/tests/test_writing_agent_tool_registry.py`:

```python
from app.services.writing_agent.agent_generation_tool_descriptors import AGENT_GENERATION_TOOL_DESCRIPTORS
```

- [x] Add:

```python
def test_agent_generation_tool_descriptors_live_in_dedicated_module():
    names = [descriptor.name for descriptor in AGENT_GENERATION_TOOL_DESCRIPTORS]

    assert names == [
        "expand_outline_window",
        "generate_chapter",
        "prepare_generate_chapter_execution",
        "execute_generate_chapter_with_approval",
        "backfill_outline_gaps",
    ]
    assert {descriptor.category for descriptor in AGENT_GENERATION_TOOL_DESCRIPTORS} == {"generation", "maintenance"}
    assert target_type_for_tool("generate_chapter") == "chapter"
    assert target_type_for_tool("prepare_generate_chapter_execution") == "chapter_generation_approval"
    assert target_type_for_tool("execute_generate_chapter_with_approval") == "chapter"
    assert target_type_for_tool("backfill_outline_gaps") == "outline"
    assert "prepare_generate_chapter_execution" in non_blocking_report_tool_names()
    assert "execute_generate_chapter_with_approval" not in non_blocking_report_tool_names()
```

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_agent_generation_tool_descriptors_live_in_dedicated_module -q
```

Expected: FAIL because `agent_generation_tool_descriptors.py` does not exist.

### Task 2: RED Adapter Boundary Test

- [x] Add import in `backend/tests/test_writing_agent_tool_executor.py`:

```python
from app.services.writing_agent.agent_generation_tool_adapters import build_agent_generation_tool_adapters
```

- [x] Add:

```python
def test_agent_generation_tool_adapters_live_in_dedicated_module():
    adapters = build_agent_generation_tool_adapters(approval_tool_metadata_provider=lambda plan: {})
    names = list(adapters)

    assert names == [
        "generate_chapter",
        "prepare_generate_chapter_execution",
        "execute_generate_chapter_with_approval",
        "expand_outline_window",
        "backfill_outline_gaps",
    ]
    assert adapters["generate_chapter"].mutability == "write"
    assert adapters["prepare_generate_chapter_execution"].mutability == "read"
    assert adapters["execute_generate_chapter_with_approval"].mutability == "write"
    assert adapters["expand_outline_window"].mutability == "write"
    assert adapters["backfill_outline_gaps"].handler.__name__ == "_backfill_outline_gaps"
```

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py::test_agent_generation_tool_adapters_live_in_dedicated_module -q
```

Expected: FAIL because `agent_generation_tool_adapters.py` does not exist.

### Task 3: Extract Generation Descriptors

- [x] Create `backend/app/services/writing_agent/agent_generation_tool_descriptors.py`.
- [x] Move/copy local schema constants:
  - `_CHAPTER_PARAMS`
  - `_WINDOW_PARAMS`
  - `_OUTLINE_WINDOW_OUTPUT`
- [x] Move the five descriptor blocks into `AGENT_GENERATION_TOOL_DESCRIPTORS`.
- [x] In `tool_registry.py`, import and spread:

```python
from app.services.writing_agent.agent_generation_tool_descriptors import AGENT_GENERATION_TOOL_DESCRIPTORS

...
    *AGENT_GENERATION_TOOL_DESCRIPTORS,
```

- [x] Remove inline descriptor blocks from `tool_registry.py`.

### Task 4: Extract Generation Adapters

- [x] Create `backend/app/services/writing_agent/agent_generation_tool_adapters.py`.
- [x] Move the five adapter handlers from `tool_executor.py`.
- [x] Add builder:

```python
def build_agent_generation_tool_adapters(
    *,
    approval_tool_metadata_provider: Callable[[dict[str, Any] | None], dict[str, dict[str, Any]]],
) -> dict[str, WritingAgentToolAdapter]:
    ...
```

- [x] In `tool_executor.py`, import and merge:

```python
from app.services.writing_agent.agent_generation_tool_adapters import build_agent_generation_tool_adapters

...
_STATIC_TOOL_ADAPTERS.update(
    build_agent_generation_tool_adapters(approval_tool_metadata_provider=_approval_tool_metadata_by_name)
)
```

- [x] Remove inline handlers and adapter entries from `tool_executor.py`.

### Task 5: Verification

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_agent_generation_tool_descriptors_live_in_dedicated_module -q
pytest backend/tests/test_writing_agent_tool_executor.py::test_agent_generation_tool_adapters_live_in_dedicated_module -q
```

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py -q
pytest backend/tests/test_writing_agent_tool_executor.py -k "agent_generation or generate_chapter or prepare_generate_chapter_execution or execute_generate_chapter_with_approval or expand_outline_window or backfill_outline_gaps" -q
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
docs/superpowers/notes/long-memory-agent/2026-05-23-phase180-agent-generation-tool-modules.md
```

- [x] Commit and push:

```powershell
git add backend/app/services/writing_agent/agent_generation_tool_descriptors.py backend/app/services/writing_agent/agent_generation_tool_adapters.py backend/app/services/writing_agent/tool_registry.py backend/app/services/writing_agent/tool_executor.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase180-agent-generation-tool-modules.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase180-agent-generation-tool-modules.md
git commit -m "refactor: split agent generation tools"
git push origin main
```
