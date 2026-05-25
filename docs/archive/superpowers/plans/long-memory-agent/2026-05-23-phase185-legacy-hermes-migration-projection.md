# Phase185 Legacy Hermes Migration Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 增加只读迁移投影工具，明确 legacy Hermes action 到 Agent-native 工具的迁移路线。

**Architecture:** 新增 `inspect_legacy_hermes_action_migration` 作为 preflight/read 工具，读取 `inspect_agent_tool_contracts` 的 execution route 事实，输出三个 legacy Hermes action 的 preview / approval / execute 拆分建议、门禁字段、迁移顺序和风险。该阶段不新增 adapter、不改变运行时。

**Tech Stack:** Python 3、pytest、Writing Agent service layer。

---

## Files

- Modify: `backend/app/services/writing_agent/agent_core_tool_descriptors.py`
  - Add descriptor for `inspect_legacy_hermes_action_migration`.
- Modify: `backend/app/services/writing_agent/agent_core_tool_adapters.py`
  - Add static adapter for `inspect_legacy_hermes_action_migration`.
- Create: `backend/app/services/writing_agent/legacy_hermes_migration_projection.py`
  - Export `inspect_legacy_hermes_action_migration(...)`.
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
  - Update core descriptor module boundary list.
  - Add descriptor contract assertions.
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
  - Update core adapter boundary list.
  - Add metadata and execution tests.

## Success Criteria

- New tool is internal, category `preflight`, non-blocking report, target type `agent_tool_migration_projection`.
- Output includes three tools:
  - `generate_setup`
  - `generate_storyline`
  - `generate_outline`
- Each item reports:
  - `current_execution_route == "legacy_action_fallback"`
  - `recommended_agent_native_shape` with `preview_tool`, `approval_tool`, `execute_tool`.
  - `required_guards` including `confirm_execute` and a hash field.
- Recommended next tools include `inspect_agent_tool_contracts`.
- No runtime dispatch behavior changes.

## Non-Scope

- Do not add static adapters for the legacy Hermes actions.
- Do not call `ActionExecutionService` from tool executor.
- Do not change slash commands or existing legacy action fallback.

## Tasks

### Task 1: RED Registry Test

- [x] Update `test_agent_core_tool_descriptors_live_in_dedicated_module` expected names to include `inspect_legacy_hermes_action_migration` after `inspect_agent_tool_contracts`.
- [x] Add:

```python
def test_agent_tool_registry_includes_legacy_hermes_migration_projection():
    descriptor = get_agent_tool_descriptor("inspect_legacy_hermes_action_migration")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "preflight"
    assert descriptor.target_type == "agent_tool_migration_projection"
    assert "inspect_legacy_hermes_action_migration" in allowed_tool_names()
    assert "inspect_legacy_hermes_action_migration" in non_blocking_report_tool_names()
```

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_agent_core_tool_descriptors_live_in_dedicated_module backend/tests/test_writing_agent_tool_registry.py::test_agent_tool_registry_includes_legacy_hermes_migration_projection -q
```

Expected: FAIL because descriptor does not exist.

### Task 2: RED Executor Test

- [x] Update `test_agent_core_tool_adapters_live_in_dedicated_module` expected names to include `inspect_legacy_hermes_action_migration` after `inspect_agent_tool_contracts`.
- [x] Add metadata test:

```python
def test_tool_executor_exposes_legacy_hermes_migration_projection_metadata():
    metadata = writing_agent_tool_adapter_metadata("inspect_legacy_hermes_action_migration")

    assert metadata == {
        "tool_name": "inspect_legacy_hermes_action_migration",
        "adapter_type": "static",
        "category": "preflight",
        "mutability": "read",
        "handler_name": "_inspect_legacy_hermes_action_migration",
    }
```

- [x] Add dispatch test:

```python
@pytest.mark.asyncio
async def test_tool_executor_handles_legacy_hermes_migration_projection(db_session):
    project = Project(name="Legacy Hermes Migration")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="inspect_legacy_hermes_action_migration"),
    )

    assert result.handled is True
    assert result.output["status"] == "completed"
    assert result.output["summary"]["legacy_action_count"] == 3
    tools_by_name = {item["tool_name"]: item for item in result.output["tools"]}
    assert set(tools_by_name) == {"generate_setup", "generate_storyline", "generate_outline"}
    assert tools_by_name["generate_setup"]["current_execution_route"] == "legacy_action_fallback"
    assert tools_by_name["generate_setup"]["recommended_agent_native_shape"]["preview_tool"] == "preview_generate_setup_execution"
    assert "confirm_execute" in tools_by_name["generate_setup"]["required_guards"]
    assert "inspect_agent_tool_contracts" in result.output["recommended_next_tools"]
```

- [x] Run the new tests. Expected: FAIL because adapter/tool does not exist.

### Task 3: Implement Projection Module

- [x] Create `backend/app/services/writing_agent/legacy_hermes_migration_projection.py`.
- [x] Implement static list for three legacy actions.
- [x] Use current descriptor and adapter metadata to compute current route.
- [x] Return:

```python
{
    "status": "completed",
    "version": "phase185.legacy_hermes_migration_projection.v1",
    "summary": {...},
    "tools": [...],
    "recommended_next_tools": ["inspect_agent_tool_contracts"],
    "trace": {"source": "inspect_legacy_hermes_action_migration"},
}
```

### Task 4: Wire Descriptor and Adapter

- [x] Add descriptor in `agent_core_tool_descriptors.py`.
- [x] Add adapter in `agent_core_tool_adapters.py`.
- [x] Keep mutability read and category preflight.

### Task 5: Verification

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_agent_core_tool_descriptors_live_in_dedicated_module backend/tests/test_writing_agent_tool_registry.py::test_agent_tool_registry_includes_legacy_hermes_migration_projection -q
pytest backend/tests/test_writing_agent_tool_executor.py -k "legacy_hermes_migration or agent_core_tool_adapters_live" -q
pytest backend/tests/test_writing_agent_tool_aggregation_boundaries.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py -q
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
docs/superpowers/notes/long-memory-agent/2026-05-23-phase185-legacy-hermes-migration-projection.md
```

- [ ] Commit and push:

```powershell
git add backend/app/services/writing_agent/legacy_hermes_migration_projection.py backend/app/services/writing_agent/agent_core_tool_descriptors.py backend/app/services/writing_agent/agent_core_tool_adapters.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase185-legacy-hermes-migration-projection.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase185-legacy-hermes-migration-projection.md
git commit -m "feat: project legacy hermes migration path"
git push origin main
```
