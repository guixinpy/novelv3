# Phase190 Route Preference Wrapper Projection Report

## Scope

增强 `inspect_agent_route_preference_projection`，让 setup / storyline / outline / chapter 的生成入口都推荐 Agent approval wrapper 链路，但不改变真实 slash/dialog runtime 路由。

## Implementation

- 将 `slash_command_route.py` 中 chapter-only 的 approved chain 常量泛化为 `APPROVED_GENERATION_CHAINS`。
- 新增 setup/storyline/outline 推荐链：
  - `generate_setup` -> `prepare_generate_setup_execution` -> `execute_generate_setup_with_approval`
  - `generate_storyline` -> `prepare_generate_storyline_execution` -> `execute_generate_storyline_with_approval`
  - `generate_outline` -> `prepare_generate_outline_execution` -> `execute_generate_outline_with_approval`
- 保留 chapter 原有推荐链。
- 保持 route projection 的 runtime 语义不变：
  - `runtime_tool_name == current_tool_name`
  - `runtime_route_changed == False`
  - `runtime_behavior_changed == False`

## Subagent Check

使用 explorer 子代理做只读检查。结论：

- 只应修改 `slash_command_route.py` 的 projection 推荐层。
- 不应修改 `dialog_control_plane.py`、`dialog_agent_routes.py`、`chat_commands.py` 等真实 runtime 路由。
- 测试需锁定推荐链、缺失 wrapper 降级、runtime 不变三个点。

## Validation

RED:

```powershell
pytest backend/tests/test_writing_agent_route_preference.py -q
# setup route still preferred ["generate_setup"]

pytest backend/tests/test_writing_agent_tool_executor.py -k "route_preference_projection" -q
# setup route still preferred ["generate_setup"]
```

GREEN / T1:

```powershell
pytest backend/tests/test_writing_agent_route_preference.py -q
# 5 passed

pytest backend/tests/test_writing_agent_tool_executor.py -k "route_preference_projection" -q
# 2 passed, 114 deselected

python -m compileall backend/app/services/writing_agent
# exit 0
```

T2:

```powershell
pytest backend/tests/test_writing_agent_tool_aggregation_boundaries.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_route_preference.py -q
# 177 passed

python -m compileall backend/app/services/writing_agent
# exit 0
```

## Novel Progress

本阶段未推进小说正文生成。原因：Phase190 是路由投影阶段，目标是让 Agent 在不改变 runtime 的前提下获得下一步迁移建议。

## Next Phase

建议 Phase191 聚焦 dialog control plane 的只读预检：

- 增加一个 projection/report，展示 pending dialog action 当前 runtime 工具与推荐 approval wrapper 的差异。
- 仍不直接切换真实执行路径。
- 先让前端或 Agent 可解释“为什么建议进入 prepare/execute 审批链”。
