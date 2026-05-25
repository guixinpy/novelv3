# Phase182 Hermes Action Descriptor Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Writing Agent registry 中剩余 legacy Hermes action descriptors 拆成独立模块。

**Architecture:** 新增 `hermes_action_tool_descriptors.py`，只承载 `generate_setup`、`generate_storyline`、`generate_outline` 三个 legacy public descriptors。`tool_registry.py` 继续保留工具计划、可用性诊断与聚合职责，不再内联任何 `AgentToolDescriptor(...)`。

**Tech Stack:** Python 3、pytest、Writing Agent service layer。

---

## Files

- Create: `backend/app/services/writing_agent/hermes_action_tool_descriptors.py`
  - Export `HERMES_ACTION_AGENT_TOOL_DESCRIPTORS`.
  - Own `_STATUS_OUTPUT` and command args schema.
- Modify: `backend/app/services/writing_agent/tool_registry.py`
  - Import and spread `HERMES_ACTION_AGENT_TOOL_DESCRIPTORS`.
  - Remove inline legacy Hermes descriptor blocks.
  - Remove now-unused `_object_schema` import and `_STATUS_OUTPUT`.
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
  - Add descriptor module boundary test.

## Success Criteria

- `tool_registry.py` no longer defines any `AgentToolDescriptor(...)` inline.
- The three legacy descriptors remain public, category `generation`, module `hermes`, and keep existing availability checks:
  - `generate_setup`: `project_exists`
  - `generate_storyline`: `setup_exists`
  - `generate_outline`: `setup_exists`, `storyline_exists`
- Legacy tools remain unhandled by static executor adapters. No adapter is added in this phase.

## Non-Scope

- Do not add static adapters for `generate_setup`, `generate_storyline`, or `generate_outline`.
- Do not change slash-command routing for `setup` / `storyline` / `outline`.
- Do not change Hermes generation implementation or public API behavior.

## Tasks

### Task 1: RED Descriptor Boundary Test

- [x] Add import in `backend/tests/test_writing_agent_tool_registry.py`:

```python
from app.services.writing_agent.hermes_action_tool_descriptors import HERMES_ACTION_AGENT_TOOL_DESCRIPTORS
```

- [x] Add:

```python
def test_hermes_action_tool_descriptors_live_in_dedicated_module():
    names = [descriptor.name for descriptor in HERMES_ACTION_AGENT_TOOL_DESCRIPTORS]

    assert names == [
        "generate_setup",
        "generate_storyline",
        "generate_outline",
    ]
    assert {descriptor.module for descriptor in HERMES_ACTION_AGENT_TOOL_DESCRIPTORS} == {"hermes"}
    assert {descriptor.category for descriptor in HERMES_ACTION_AGENT_TOOL_DESCRIPTORS} == {"generation"}
    assert all(not descriptor.internal for descriptor in HERMES_ACTION_AGENT_TOOL_DESCRIPTORS)
    assert target_type_for_tool("generate_setup") == "setup"
    assert target_type_for_tool("generate_storyline") == "storyline"
    assert target_type_for_tool("generate_outline") == "outline"
    assert "generate_setup" in allowed_tool_names()
```

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_hermes_action_tool_descriptors_live_in_dedicated_module -q
```

Expected: FAIL because `hermes_action_tool_descriptors.py` does not exist.

### Task 2: Extract Hermes Action Descriptors

- [x] Create `backend/app/services/writing_agent/hermes_action_tool_descriptors.py`.
- [x] Move the three descriptor blocks into `HERMES_ACTION_AGENT_TOOL_DESCRIPTORS`.
- [x] In `tool_registry.py`, import and spread:

```python
from app.services.writing_agent.hermes_action_tool_descriptors import HERMES_ACTION_AGENT_TOOL_DESCRIPTORS

...
    *HERMES_ACTION_AGENT_TOOL_DESCRIPTORS,
```

- [x] Remove inline descriptor blocks, `_STATUS_OUTPUT`, and unused `_object_schema` import from `tool_registry.py`.

### Task 3: Verification

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_hermes_action_tool_descriptors_live_in_dedicated_module -q
pytest backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py -q
pytest backend/tests/test_writing_agent_tool_executor.py -k "legacy_generation_tools_unhandled or slash_command_route or static_writing_agent_tool_adapter_names" -q
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
docs/superpowers/notes/long-memory-agent/2026-05-23-phase182-hermes-action-descriptor-module.md
```

- [x] Commit and push:

```powershell
git add backend/app/services/writing_agent/hermes_action_tool_descriptors.py backend/app/services/writing_agent/tool_registry.py backend/tests/test_writing_agent_tool_registry.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase182-hermes-action-descriptor-module.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase182-hermes-action-descriptor-module.md
git commit -m "refactor: split hermes action descriptors"
git push origin main
```
