# Phase178 Agent Core Tool Modules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Writing Agent 的 preflight/planning/approval/route-inspection 核心工具拆成独立 Agent core 能力域模块。

**Architecture:** `tool_registry.py` 继续聚合 descriptor，`tool_executor.py` 继续聚合 adapter。新增 `agent_core_tool_descriptors.py` 承载 category=`preflight` 的核心工具 descriptor；新增 `agent_core_tool_adapters.py` 提供 `build_agent_core_tool_adapters(...)`，通过 provider 延迟读取当前 static adapter metadata 和工具名集合，避免核心 handler 直接反向依赖 executor 全局状态。

**Tech Stack:** Python 3、pytest、Writing Agent service layer。

---

## Files

- Create: `backend/app/services/writing_agent/agent_core_tool_descriptors.py`
  - Export `AGENT_CORE_TOOL_DESCRIPTORS`.
  - Own approval/write-gate structured output schema constants used only by preflight/core descriptors.
- Create: `backend/app/services/writing_agent/agent_core_tool_adapters.py`
  - Export `build_agent_core_tool_adapters(...)`.
  - Own preflight/planning/approval/route-inspection handlers and local parsing helpers.
- Modify: `backend/app/services/writing_agent/tool_registry.py`
  - Import and spread `AGENT_CORE_TOOL_DESCRIPTORS`.
  - Remove inline preflight/core descriptor blocks and now-unused output schema constants.
- Modify: `backend/app/services/writing_agent/tool_executor.py`
  - Import and merge `build_agent_core_tool_adapters(...)`.
  - Remove inline preflight/core static handler functions and adapter entries.
  - Keep `preflight_writing` as injected metadata special case.
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
  - Add descriptor module boundary test.
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
  - Add adapter module boundary test.

## Success Criteria

- `tool_registry.py` no longer defines these core descriptors inline:
  - `describe_agent_tools`
  - `plan_writing_agent_run`
  - `plan_dialog_intent_agent_run`
  - `preview_agent_plan_approval_contract`
  - `verify_agent_plan_approval_contract`
  - `plan_recovery_tools`
  - `plan_recommended_followups`
  - `inspect_agent_slash_command_route`
  - `inspect_agent_dialog_route_projection`
  - `inspect_agent_route_preference_projection`
  - `inspect_agent_intent_projection`
  - `inspect_agent_tool_contracts`
  - `inspect_agent_write_gate_coverage`
  - `inspect_agent_mutation_fingerprints`
  - `preflight_writing`
- `tool_executor.py` no longer defines matching static preflight/core handlers inline.
- `preflight_writing` remains injected, not a static adapter.
- Existing tool behavior, metadata, target type, non-blocking flag, and route projection tests remain green.

## Non-Scope

- Do not move generation tools:
  - `generate_chapter`
  - `prepare_generate_chapter_execution`
  - `execute_generate_chapter_with_approval`
  - `expand_outline_window`
- Do not move task queue tools:
  - `inspect_agent_job_projection`
  - `plan_chapter_conflict_recovery`
- Do not move trace or longform-memory tools in this phase.

## Tasks

### Task 1: RED Descriptor Boundary Test

- [x] Add import in `backend/tests/test_writing_agent_tool_registry.py`:

```python
from app.services.writing_agent.agent_core_tool_descriptors import AGENT_CORE_TOOL_DESCRIPTORS
```

- [x] Add:

```python
def test_agent_core_tool_descriptors_live_in_dedicated_module():
    names = [descriptor.name for descriptor in AGENT_CORE_TOOL_DESCRIPTORS]

    assert names == [
        "describe_agent_tools",
        "plan_writing_agent_run",
        "plan_dialog_intent_agent_run",
        "preview_agent_plan_approval_contract",
        "verify_agent_plan_approval_contract",
        "plan_recovery_tools",
        "plan_recommended_followups",
        "inspect_agent_slash_command_route",
        "inspect_agent_dialog_route_projection",
        "inspect_agent_route_preference_projection",
        "inspect_agent_intent_projection",
        "inspect_agent_tool_contracts",
        "inspect_agent_write_gate_coverage",
        "inspect_agent_mutation_fingerprints",
        "preflight_writing",
    ]
    assert {descriptor.category for descriptor in AGENT_CORE_TOOL_DESCRIPTORS} == {"preflight"}
    assert {descriptor.module for descriptor in AGENT_CORE_TOOL_DESCRIPTORS} == {"writing_agent"}
    assert all(descriptor.internal for descriptor in AGENT_CORE_TOOL_DESCRIPTORS)
    assert target_type_for_tool("preview_agent_plan_approval_contract") == "agent_plan_approval_contract"
    assert target_type_for_tool("inspect_agent_write_gate_coverage") == "agent_write_gate_coverage"
    assert "plan_writing_agent_run" in non_blocking_report_tool_names()
    assert "preflight_writing" not in non_blocking_report_tool_names()
```

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_agent_core_tool_descriptors_live_in_dedicated_module -q
```

Expected: FAIL because `agent_core_tool_descriptors.py` does not exist.

### Task 2: RED Adapter Boundary Test

- [x] Add import in `backend/tests/test_writing_agent_tool_executor.py`:

```python
from app.services.writing_agent.agent_core_tool_adapters import build_agent_core_tool_adapters
```

- [x] Add:

```python
def test_agent_core_tool_adapters_live_in_dedicated_module():
    adapters = build_agent_core_tool_adapters(
        adapter_metadata_by_name_provider=lambda: {},
        static_adapter_tool_names_provider=lambda: set(),
    )
    names = list(adapters)

    assert names == [
        "describe_agent_tools",
        "plan_writing_agent_run",
        "plan_dialog_intent_agent_run",
        "preview_agent_plan_approval_contract",
        "verify_agent_plan_approval_contract",
        "plan_recovery_tools",
        "plan_recommended_followups",
        "inspect_agent_slash_command_route",
        "inspect_agent_dialog_route_projection",
        "inspect_agent_route_preference_projection",
        "inspect_agent_intent_projection",
        "inspect_agent_tool_contracts",
        "inspect_agent_write_gate_coverage",
        "inspect_agent_mutation_fingerprints",
    ]
    assert "preflight_writing" not in names
    assert {adapter.category for adapter in adapters.values()} == {"preflight"}
    assert {adapter.mutability for adapter in adapters.values()} == {"read"}
    assert adapters["verify_agent_plan_approval_contract"].handler.__name__ == "_verify_agent_plan_approval_contract"
    assert adapters["inspect_agent_intent_projection"].handler.__name__ == "_inspect_agent_intent_projection"
```

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py::test_agent_core_tool_adapters_live_in_dedicated_module -q
```

Expected: FAIL because `agent_core_tool_adapters.py` does not exist.

### Task 3: Extract Agent Core Descriptors

- [x] Create `backend/app/services/writing_agent/agent_core_tool_descriptors.py`.
- [x] Use `AgentToolDescriptor` and `object_schema`.
- [x] Move/copy core-only schema constants:
  - `_AGENT_PLAN_APPROVAL_CONTRACT_OUTPUT`
  - `_AGENT_PLAN_APPROVAL_VERIFICATION_OUTPUT`
  - `_AGENT_WRITE_GATE_COVERAGE_OUTPUT`
- [x] Move the 15 core descriptor blocks into `AGENT_CORE_TOOL_DESCRIPTORS`.
- [x] In `tool_registry.py`, import and spread:

```python
from app.services.writing_agent.agent_core_tool_descriptors import AGENT_CORE_TOOL_DESCRIPTORS

...
    *AGENT_CORE_TOOL_DESCRIPTORS,
```

- [x] Remove inline core descriptor blocks and now-unused schema constants from `tool_registry.py`.

### Task 4: Extract Agent Core Adapters

- [x] Create `backend/app/services/writing_agent/agent_core_tool_adapters.py`.
- [x] Move the 14 static core adapter handlers from `tool_executor.py`.
- [x] Keep `preflight_writing` out of `build_agent_core_tool_adapters(...)` because it is injected by `execute_writing_agent_tool(...)`.
- [x] Add provider-driven builder:

```python
def build_agent_core_tool_adapters(
    *,
    adapter_metadata_by_name_provider: Callable[[], dict[str, dict[str, Any]]],
    static_adapter_tool_names_provider: Callable[[], set[str]],
) -> dict[str, WritingAgentToolAdapter]:
    ...
```

- [x] In `tool_executor.py`, import and merge:

```python
from app.services.writing_agent.agent_core_tool_adapters import build_agent_core_tool_adapters

...
_STATIC_TOOL_ADAPTERS.update(
    build_agent_core_tool_adapters(
        adapter_metadata_by_name_provider=lambda: _static_adapter_metadata_by_name(),
        static_adapter_tool_names_provider=lambda: set(_STATIC_TOOL_ADAPTERS),
    )
)
```

- [x] Remove inline core handlers and adapter entries from `tool_executor.py`.

### Task 5: Verification

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_agent_core_tool_descriptors_live_in_dedicated_module -q
pytest backend/tests/test_writing_agent_tool_executor.py::test_agent_core_tool_adapters_live_in_dedicated_module -q
```

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py -q
pytest backend/tests/test_writing_agent_runs.py -k "plan_writing_agent_run or plan_dialog_intent_agent_run or preview_agent_plan_approval_contract or verify_agent_plan_approval_contract or inspect_agent_slash_command_route or inspect_agent_intent_projection" -q
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
docs/superpowers/notes/long-memory-agent/2026-05-23-phase178-agent-core-tool-modules.md
```

- [x] Commit and push:

```powershell
git add backend/app/services/writing_agent/agent_core_tool_descriptors.py backend/app/services/writing_agent/agent_core_tool_adapters.py backend/app/services/writing_agent/tool_registry.py backend/app/services/writing_agent/tool_executor.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase178-agent-core-tool-modules.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase178-agent-core-tool-modules.md
git commit -m "refactor: split agent core tools"
git push origin main
```
