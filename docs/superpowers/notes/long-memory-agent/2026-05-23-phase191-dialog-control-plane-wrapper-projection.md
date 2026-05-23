# Phase191 Dialog Control Plane Wrapper Projection Report

## Scope

新增 `inspect_agent_dialog_control_plane_projection`，用于只读展示 pending dialog action 当前 runtime 工具与推荐 Agent approval wrapper 的差异。

## Implementation

- 在 `dialog_control_plane.py` 中新增：
  - `DIALOG_CONTROL_PLANE_PROJECTION_VERSION`
  - `APPROVED_DIALOG_CONTROL_PLANE_CHAINS`
  - `inspect_agent_dialog_control_plane_projection`
- 在 `agent_core_tool_descriptors.py` 注册新 preflight descriptor。
- 在 `agent_core_tool_adapters.py` 注册新 static read adapter。
- 未修改 `SUPPORTED_DIALOG_ACTION_TO_TOOL`、`_tool_name_for_action` 或真实后台执行逻辑。

## Behavior

- setup/storyline/outline：
  - 当前 runtime tool 仍为 legacy action 工具。
  - 推荐 prepare/execute approval wrapper。
  - `runtime_behavior_changed == False`。
- chapter：
  - 当前 runtime prepare tool 仍为 `prepare_generate_chapter_execution`。
  - 带审批契约时的 execute tool 仍为 `execute_generate_chapter_with_approval`。
  - 标记为 `runtime_already_uses_approval_chain == True`。

## Validation

RED:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -k "dialog_control_plane_projection" -q
# descriptor is None

pytest backend/tests/test_writing_agent_tool_executor.py -k "dialog_control_plane_projection" -q
# handled is False / adapter metadata is None
```

GREEN / T1:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -k "dialog_control_plane_projection" -q
# 1 passed, 52 deselected

pytest backend/tests/test_writing_agent_tool_executor.py -k "dialog_control_plane_projection" -q
# 2 passed, 116 deselected

python -m compileall backend/app/services/writing_agent
# exit 0
```

T2:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -k "agent_core_tool_descriptors or dialog_control_plane_projection" -q
# 2 passed, 51 deselected

pytest backend/tests/test_writing_agent_tool_aggregation_boundaries.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py -q
# 175 passed
```

## Novel Progress

本阶段未推进小说正文生成。原因：Phase191 是对话入口 control plane 可观测性阶段，目标是为后续安全切换 execution route 做只读铺垫。

## Next Phase

建议 Phase192 开始做 dialog control plane 的 guarded route migration 预案：

- 先新增 feature-flag 或 explicit params 驱动的 prepare-chain dispatch。
- 默认保持 legacy runtime 不变。
- 用测试证明 setup/storyline/outline 可在显式 opt-in 时走 prepare wrapper。
