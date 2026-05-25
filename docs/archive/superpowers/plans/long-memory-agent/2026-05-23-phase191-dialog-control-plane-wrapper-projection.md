# Phase191 Dialog Control Plane Wrapper Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 增加 dialog control plane 的只读投影，让 Agent/前端能看到当前 pending action runtime 工具与推荐 Agent approval wrapper 的差异。

**Architecture:** 在 `dialog_control_plane.py` 中新增只读 projection，不改变 `SUPPORTED_DIALOG_ACTION_TO_TOOL`、`_tool_name_for_action` 或后台执行逻辑。通过新的 preflight 工具 `inspect_agent_dialog_control_plane_projection` 暴露投影。

**Tech Stack:** Python 3、pytest、Writing Agent service layer。

---

## Files

- Modify: `backend/app/services/writing_agent/dialog_control_plane.py`
- Modify: `backend/app/services/writing_agent/agent_core_tool_descriptors.py`
- Modify: `backend/app/services/writing_agent/agent_core_tool_adapters.py`
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
- Add: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase191-dialog-control-plane-wrapper-projection.md`

## Success Criteria

- New tool `inspect_agent_dialog_control_plane_projection` is internal, non-blocking, preflight.
- Projection reports setup/storyline/outline current runtime as legacy action tools and recommended wrapper chains.
- Projection reports chapter current runtime as already using prepare/execute approval chain.
- Projection does not change runtime dispatch.

## Non-Scope

- Do not change `SUPPORTED_DIALOG_ACTION_TO_TOOL`.
- Do not change `_tool_name_for_action`.
- Do not switch setup/storyline/outline execution to prepare tools.

## Tasks

### Task 1: RED Registry And Executor Tests

- [x] Add descriptor registry assertions for `inspect_agent_dialog_control_plane_projection`.
- [x] Add adapter metadata assertion.
- [x] Add executor test asserting:
  - `generate_setup` current runtime tool is `generate_setup`
  - recommended chain is `prepare_generate_setup_execution` -> `execute_generate_setup_with_approval`
  - `runtime_behavior_changed is False`
  - `generate_chapter` reports current prepare and execute tools.
- [x] Run expected RED:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -k "dialog_control_plane_projection" -q
pytest backend/tests/test_writing_agent_tool_executor.py -k "dialog_control_plane_projection" -q
```

### Task 2: Implement Projection

- [x] Add `DIALOG_CONTROL_PLANE_PROJECTION_VERSION`.
- [x] Add `inspect_agent_dialog_control_plane_projection(action_type=None)`.
- [x] Add helper mapping from action type to recommended wrapper chains.
- [x] Keep runtime fields derived from existing `SUPPORTED_DIALOG_ACTION_TO_TOOL` and `CHAPTER_APPROVAL_EXECUTE_TOOL`.

### Task 3: Wire Tool Descriptor And Adapter

- [x] Add descriptor in `agent_core_tool_descriptors.py`.
- [x] Add adapter in `agent_core_tool_adapters.py`.
- [x] Ensure tool appears in `test_agent_core_tool_adapters_live_in_dedicated_module` expected names.

### Task 4: Verification

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -k "dialog_control_plane_projection" -q
pytest backend/tests/test_writing_agent_tool_executor.py -k "dialog_control_plane_projection" -q
pytest backend/tests/test_writing_agent_tool_aggregation_boundaries.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py -q
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
docs/superpowers/notes/long-memory-agent/2026-05-23-phase191-dialog-control-plane-wrapper-projection.md
```

- [x] Commit and push:

```powershell
git add backend/app/services/writing_agent/dialog_control_plane.py backend/app/services/writing_agent/agent_core_tool_descriptors.py backend/app/services/writing_agent/agent_core_tool_adapters.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase191-dialog-control-plane-wrapper-projection.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase191-dialog-control-plane-wrapper-projection.md
git commit -m "feat: inspect dialog control plane routes"
git push origin main
```
