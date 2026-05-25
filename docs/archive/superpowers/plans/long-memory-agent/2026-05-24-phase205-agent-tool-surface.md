# Phase205 Agent Tool Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `describe_agent_tools` / `build_agent_tool_plan` 的工具列表中暴露最小 Agent 工具表面元数据，让 planner 能直接看到工具可见性、读写权限、确认要求和并发安全性。

**Architecture:** 不另起一套执行器权限系统；复用现有 descriptor 的命名、schema 和 `internal/non_blocking_report` 约定，在 `AgentToolDescriptor.to_public_dict()` 增加 `agent_tool_surface`。`inspect_agent_tool_contracts` 继续负责完整审计，`agent_tool_surface` 只提供 planner 所需的轻量摘要。

**Tech Stack:** Python dataclasses, existing Writing Agent tool registry, pytest.

---

## Reference Project Inputs

- OpenHuman `ToolScope` / `PermissionLevel` / `ToolCategory`：工具描述本身应携带执行边界，planner 不应只靠工具名猜测读写风险。
- Hermes `tools/registry.py`：工具 schema 和 toolset exposure 分离；工具可注册并被审计，但是否暴露给当前 agent surface 需要明确投影。
- OpenClaw inherited allow/deny：工具 surface 需要可由上层策略过滤，至少先提供稳定的权限字段。

## Files

- Modify: `backend/app/services/writing_agent/tool_descriptor_types.py`
  - 增加 descriptor 级轻量 surface 推断函数。
  - `to_public_dict()` 增加 `agent_tool_surface`。
- Modify: `backend/app/services/writing_agent/tool_registry.py`
  - `build_agent_tool_plan()` 接收可选 adapter metadata，用于真实 adapter 路径纠正 descriptor fallback。
- Modify: `backend/app/services/writing_agent/tool_executor.py`
  - 暴露 adapter metadata by-name，并包含 injected `preflight_writing`。
- Modify: `backend/app/services/writing_agent/agent_core_tool_adapters.py`
  - `describe_agent_tools` 执行时传入 adapter metadata。
- Modify: `backend/app/services/writing_agent/planner.py`, `backend/app/services/writing_agent/recovery_planner.py`
  - planner / recovery 可见性判断使用 adapter metadata 投影。
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
  - 覆盖 `build_agent_tool_plan()` 中 visible/hidden tools 均带 surface。
  - 覆盖 read/internal 工具、write 工具、guarded write 工具的基础字段。
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
  - 覆盖真实 `execute_writing_agent_tool -> describe_agent_tools` 路径。
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-24-phase205-agent-tool-surface.md`
  - 记录 RED/GREEN/T2、参考项目转译、下一阶段。

## Tasks

### Task 1: RED Tests

- [x] **Step 1: Add failing registry tests**

Add tests to `backend/tests/test_writing_agent_tool_registry.py`:

```python
def test_agent_tool_plan_exposes_agent_tool_surface_for_visible_tools(db_session):
    project = _seed_ready_project(db_session)

    plan = build_agent_tool_plan(db_session, project.id, chapter_index=2)
    visible = {tool["name"]: tool for tool in plan["visible_tools"]}

    describe_surface = visible["describe_agent_tools"]["agent_tool_surface"]
    assert describe_surface == {
        "visibility": "internal_only",
        "tool_scope": "agent_only",
        "mutability": "read",
        "permission_level": "read",
        "requires_confirmation": False,
        "parallel_safe": True,
    }

    generate_surface = visible["generate_chapter"]["agent_tool_surface"]
    assert generate_surface["visibility"] == "agent_visible"
    assert generate_surface["tool_scope"] == "agent_and_legacy_action"
    assert generate_surface["mutability"] == "write"
    assert generate_surface["permission_level"] == "write"
    assert generate_surface["requires_confirmation"] is False
    assert generate_surface["parallel_safe"] is False


def test_agent_tool_plan_exposes_guarded_write_surface_for_hidden_tools(db_session):
    project = _seed_ready_project(db_session)

    plan = build_agent_tool_plan(db_session, project.id, chapter_index=2)
    hidden = {tool["name"]: tool for tool in plan["hidden_tools"]}

    execute_surface = hidden["execute_longform_chapter_batch"]["agent_tool_surface"]
    assert execute_surface["mutability"] == "guarded_write"
    assert execute_surface["permission_level"] == "confirm_required"
    assert execute_surface["requires_confirmation"] is True
    assert execute_surface["parallel_safe"] is False
```

- [x] **Step 2: Run RED**

Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -k "agent_tool_plan_exposes_agent_tool_surface or guarded_write_surface" -q
```

Expected: FAIL with missing `agent_tool_surface`.

### Task 2: Implement Surface Projection

- [x] **Step 1: Add minimal surface helpers**

In `tool_descriptor_types.py`, add:

- `descriptor_requires_confirmation(descriptor)`
- `descriptor_mutability(descriptor)`
- `descriptor_permission_level(mutability)`
- `descriptor_tool_surface(descriptor)`

Rules mirror the existing contract snapshot:

- read prefixes / non-blocking report -> `read`
- `apply_`, `execute_`, `enqueue_`, `route_` or confirm/hash params -> `guarded_write`
- write prefixes -> `write`
- otherwise `unclassified`

- [x] **Step 2: Add surface to public dict**

Return:

```python
"agent_tool_surface": descriptor_tool_surface(self)
```

- [x] **Step 3: Run GREEN**

Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -k "agent_tool_plan_exposes_agent_tool_surface or guarded_write_surface" -q
```

Expected: PASS.

### Task 3: Validation

- [x] **Step 1: Targeted backend validation**

Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -k "agent_tool_plan or inspect_agent_tool_contracts" -q
pytest backend/tests/test_writing_agent_tool_executor.py -k "inspect_agent_tool_contracts or describe_agent_tools" -q
```

- [x] **Step 2: T2 checks**

Run:

```powershell
python -m compileall backend/app/services/writing_agent
git diff --check
rg -n "<real DeepSeek key prefix>" .
```

Expected: all pass; key scan has no matches.

### Task 4: Review, Report, Commit

- [x] **Step 1: Request focused review**

Ask reviewer to verify:

- no new execution behavior;
- surface fields match existing contract semantics;
- no circular imports;
- no sensitive data in tool surface.

- [ ] **Step 2: Update report and commit**

Commit:

```text
feat: expose agent tool surface metadata
```
