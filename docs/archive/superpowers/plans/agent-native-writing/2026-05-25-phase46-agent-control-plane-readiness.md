# Phase46: Agent Control Plane Readiness

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 Agent-callable 的 control-plane readiness 工具，将工具契约和命令契约合并为一个可审计、可推荐下一步的控制面摘要。

**Architecture:** 新建 `agent_control_plane_readiness.py` 作为纯服务，读取 `tool_contracts` 与 `agent_command_contracts` 的摘要并输出 bounded readiness。再通过 core tool descriptor + adapter 暴露为 `inspect_agent_control_plane_readiness`，供 Agent 在编排前自检。

**Tech Stack:** Python service、Writing Agent tool registry/adapter、pytest。

---

## 参考项目吸收

- hermes-agent：控制面 readiness 应该直接给 Agent loop 使用，包含状态、诊断和下一步工具。
- openclaw：工具可见性、权限和命令控制面要统一进入 control-plane policy，不分散在多个页面按钮。
- openhuman：输出只保留 bounded summary 和 provenance，不展开完整工具/命令列表。

## 成功标准

1. `inspect_agent_control_plane_readiness(...)` 输出：
   - `status`
   - `version`
   - `summary`
   - `diagnostics`
   - `recommended_next_tools`
   - `control_surfaces`
   - `trace`
2. 工具契约或命令契约有 gap 时，`status == "degraded"` 并推荐对应检查工具。
3. 无 gap 时，`status == "ready"`。
4. `inspect_agent_control_plane_readiness` 注册为 Agent tool descriptor 和 static adapter。
5. 不展开完整 `tools` / `commands` 列表，避免成为另一个大对象透传。

## Task 1: Pure Readiness Service

**Files:**
- Create: `backend/app/services/writing_agent/agent_control_plane_readiness.py`
- Test: `backend/tests/test_agent_control_plane_readiness.py`

- [ ] **Step 1: Write failing tests**

Create tests:

```python
from app.services.writing_agent.agent_control_plane_readiness import inspect_agent_control_plane_readiness


def test_agent_control_plane_readiness_reports_ready_when_contracts_are_clean():
    output = inspect_agent_control_plane_readiness(
        tool_contract_snapshot_provider=lambda: {
            "status": "completed",
            "summary": {"total_tools": 3, "tools_needing_work": 0, "gap_count": 0},
            "coverage": {"adapter_coverage_ratio": 1.0},
        },
        command_contract_provider=lambda: {
            "status": "completed",
            "version": "phase38.agent_command_contracts.v1",
            "summary": {
                "total_commands": 4,
                "agent_control_commands": 2,
                "commands_with_control_projection": 2,
                "gap_count": 0,
            },
        },
    )

    assert output["status"] == "ready"
    assert output["summary"]["total_gap_count"] == 0
    assert output["summary"]["agent_control_commands"] == 2
    assert output["diagnostics"] == []
    assert output["recommended_next_tools"] == ["inspect_agent_health_projection"]


def test_agent_control_plane_readiness_reports_degraded_contract_gaps():
    output = inspect_agent_control_plane_readiness(
        tool_contract_snapshot_provider=lambda: {
            "status": "completed",
            "summary": {"total_tools": 5, "tools_needing_work": 2, "gap_count": 3},
            "coverage": {"adapter_coverage_ratio": 0.6},
        },
        command_contract_provider=lambda: {
            "status": "completed",
            "version": "phase38.agent_command_contracts.v1",
            "summary": {
                "total_commands": 4,
                "agent_control_commands": 2,
                "commands_with_control_projection": 1,
                "gap_count": 1,
            },
        },
    )

    assert output["status"] == "degraded"
    assert output["summary"]["total_gap_count"] == 4
    assert [item["code"] for item in output["diagnostics"]] == [
        "agent_tool_contract_gaps",
        "agent_command_contract_gaps",
    ]
    assert output["recommended_next_tools"] == [
        "inspect_agent_tool_contracts",
        "inspect_agent_command_contracts",
        "inspect_agent_health_projection",
    ]
```

- [ ] **Step 2: Verify RED**

Run:

```powershell
pytest backend/tests/test_agent_control_plane_readiness.py -q
```

Expected: import failure because service does not exist.

- [ ] **Step 3: Implement service**

Implement the pure service with injected providers and default providers:

- Default tool snapshot: `build_agent_tool_contract_snapshot(adapter_metadata_by_name=..., include_gap_details=False)`.
- Default command snapshot: `inspect_agent_command_contracts(adapter_names_provider=lambda: static_adapter_tool_names or set())`.
- Summary fields:
  - `total_tools`
  - `tools_needing_work`
  - `tool_gap_count`
  - `total_commands`
  - `agent_control_commands`
  - `commands_with_control_projection`
  - `command_gap_count`
  - `total_gap_count`
- Diagnostics:
  - `agent_tool_contract_gaps`
  - `agent_command_contract_gaps`
- Recommended tools: gap-specific tools plus `inspect_agent_health_projection`, deduped.

- [ ] **Step 4: Verify GREEN**

Run:

```powershell
pytest backend/tests/test_agent_control_plane_readiness.py -q
```

Expected: PASS.

## Task 2: Agent Tool Descriptor and Adapter

**Files:**
- Modify: `backend/app/services/writing_agent/agent_core_tool_descriptors.py`
- Modify: `backend/app/services/writing_agent/agent_core_tool_adapters.py`
- Test: `backend/tests/test_writing_agent_tool_registry.py`
- Test: `backend/tests/test_writing_agent_tool_executor.py`

- [ ] **Step 1: Write failing registry and executor tests**

Add registry test:

```python
def test_agent_tool_registry_includes_inspect_agent_control_plane_readiness():
    descriptor = get_agent_tool_descriptor("inspect_agent_control_plane_readiness")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "preflight"
    assert descriptor.target_type == "agent_control_plane_readiness"
    assert descriptor.output_schema["properties"]["control_surfaces"]["type"] == "object"
    assert "inspect_agent_control_plane_readiness" in allowed_tool_names()
    assert "inspect_agent_control_plane_readiness" in non_blocking_report_tool_names()
```

Add executor metadata and dispatch assertions:

```python
def test_tool_executor_exposes_inspect_agent_control_plane_readiness_adapter_metadata():
    assert writing_agent_tool_adapter_metadata("inspect_agent_control_plane_readiness") == {
        "tool_name": "inspect_agent_control_plane_readiness",
        "adapter_type": "static",
        "category": "preflight",
        "mutability": "read",
        "handler_name": "_inspect_agent_control_plane_readiness",
    }
```

```python
@pytest.mark.asyncio
async def test_tool_executor_handles_inspect_agent_control_plane_readiness(db_session):
    project = Project(name="Control Plane Readiness")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-control-plane"),
        WritingAgentToolRequest(tool_name="inspect_agent_control_plane_readiness"),
    )

    assert result.handled is True
    assert result.output["status"] in {"ready", "degraded"}
    assert result.output["summary"]["agent_control_commands"] == 2
    assert "tool_contracts" in result.output["control_surfaces"]
    assert "command_contracts" in result.output["control_surfaces"]
    assert "inspect_agent_health_projection" in result.output["recommended_next_tools"]
```

- [ ] **Step 2: Verify RED**

Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -k "control_plane_readiness" -q
pytest backend/tests/test_writing_agent_tool_executor.py -k "control_plane_readiness" -q
```

Expected: FAIL because descriptor and adapter are absent.

- [ ] **Step 3: Register descriptor and adapter**

Add descriptor after `inspect_agent_health_projection` or near contract tools:

- name: `inspect_agent_control_plane_readiness`
- category: `preflight`
- target_type: `agent_control_plane_readiness`
- internal: `True`
- non_blocking_report: `True`
- mutability: read via adapter.

Add adapter to `build_agent_core_tool_adapters(...)` and handler `_inspect_agent_control_plane_readiness(...)`.

- [ ] **Step 4: Verify GREEN**

Run:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -k "control_plane_readiness" -q
pytest backend/tests/test_writing_agent_tool_executor.py -k "control_plane_readiness" -q
```

Expected: PASS.

## Task 3: Phase Verification and Report

**Files:**
- Create: `docs/superpowers/notes/agent-native-writing/2026-05-25-phase46-agent-control-plane-readiness.md`

- [ ] **Step 1: Run targeted verification**

Run:

```powershell
pytest backend/tests/test_agent_control_plane_readiness.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py -k "control_plane_readiness" -q
git diff --check
```

- [ ] **Step 2: Write phase report**

Record RED evidence, GREEN evidence, changed files, and next-phase recommendation.
