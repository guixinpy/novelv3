# Phase208 Profile Scoped Describe Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `describe_agent_tools` 支持 `agent_profile` 参数，并在指定 profile 时返回 profile-scoped 工具面，使模型实际消费收窄后的工具集。

**Architecture:** 默认无 `agent_profile` 时保持完整 tool plan 输出不变；指定 profile 时从 Phase207 的 `agent_profile_tool_projection` 派生 scoped `visible_tools` / `hidden_tools`，并附加 profile scope metadata。该阶段仍不改变 executor 权限，只改变 `describe_agent_tools` 的工具发现输出。

**Tech Stack:** Python, existing Writing Agent tool registry, pytest.

---

## Reference Project Inputs

- Hermes Agent：模型收到的是当前 toolset 过滤后的工具定义，而不是全局工具表。
- OpenHuman：session builder 根据 agent definition 过滤可见工具。
- OpenClaw：effective inventory 可继续保留全量证据，但 agent-facing tool list 应由 policy pipeline 收窄。

## Files

- Modify: `backend/app/services/writing_agent/agent_tool_surface_policy.py`
  - 增加 `apply_agent_profile_tool_scope(plan, agent_profile)`。
- Modify: `backend/app/services/writing_agent/agent_core_tool_descriptors.py`
  - `describe_agent_tools` input schema 增加可选 `agent_profile`。
  - output schema 增加 `agent_profile_scope`。
- Modify: `backend/app/services/writing_agent/agent_core_tool_adapters.py`
  - `_describe_agent_tools` 读取 `agent_profile` 并应用 profile scope。
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
  - 覆盖 `describe_agent_tools` profile-scoped 输出和默认兼容输出。
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-24-phase208-profile-scoped-describe-tools.md`
  - 记录 RED/GREEN/T2、审查、参考项目转译。

## Tasks

### Task 1: RED Tests

- [x] **Step 1: Add profile-scoped describe test**

Add an async test in `backend/tests/test_writing_agent_tool_executor.py`:

```python
@pytest.mark.asyncio
async def test_tool_executor_scopes_describe_agent_tools_by_agent_profile(db_session):
    project = _seed_profile_scope_project(db_session)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-profile-scope"),
        WritingAgentToolRequest(
            tool_name="describe_agent_tools",
            params={"chapter_index": 2, "agent_profile": "reviewer_worker"},
        ),
    )

    visible = {tool["name"] for tool in result.output["visible_tools"]}
    hidden = {tool["name"] for tool in result.output["hidden_tools"]}

    assert result.output["agent_profile_scope"]["status"] == "applied"
    assert result.output["agent_profile_scope"]["agent_profile"] == "reviewer_worker"
    assert "review_chapter_quality" in visible
    assert "generate_chapter" not in visible
    assert "generate_chapter" in hidden
```

- [x] **Step 2: Add default compatibility assertion**

Extend the existing `test_tool_executor_handles_describe_agent_tools` to assert:

```python
assert result.output["agent_profile_scope"]["status"] == "not_requested"
```

- [x] **Step 3: Run RED**

Run:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "describe_agent_tools" -q
```

Expected: FAIL because `agent_profile_scope` and scoping are not implemented.

### Task 2: Implement Scoped Projection

- [x] **Step 1: Add helper**

Implement `apply_agent_profile_tool_scope(plan, agent_profile)` in `agent_tool_surface_policy.py`:

- return original plan plus `agent_profile_scope.status = "not_requested"` when profile is empty;
- return original plan plus `agent_profile_scope.status = "unknown_profile"` when profile is unknown;
- when known, filter `visible_tools` to `allowed_visible_tools`;
- move profile-blocked visible tools into `hidden_tools` with diagnostic code `profile_filtered`;
- keep hidden tools that are in `allowed_hidden_tools`;
- recompute `toolsets` from scoped visible tools.

- [x] **Step 2: Wire descriptor and adapter**

- Add `agent_profile` to `describe_agent_tools` input schema.
- In `_describe_agent_tools`, call `apply_agent_profile_tool_scope(...)`.

### Task 3: Validation

- [x] **Step 1: Targeted backend validation**

Run:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "describe_agent_tools" -q
pytest backend/tests/test_writing_agent_tool_registry.py -k "agent_profile_tool_projection or tool_policy_projection" -q
pytest backend/tests/test_writing_agent_planner.py -q
```

- [x] **Step 2: T2 checks**

Run:

```powershell
python -m compileall backend/app/services/writing_agent
git diff --check
```

### Task 4: Review, Report, Commit

- [x] **Step 1: Focused review**

Ask reviewer to verify:

- default `describe_agent_tools` output remains compatible;
- profile-scoped output does not change executor behavior;
- profile-filtered diagnostics are explicit;
- output does not include project content or secrets.

- [ ] **Step 2: Update report and commit**

Commit:

```text
feat: scope described tools by agent profile
```
