# Phase189 Legacy Hermes Wrapper Readiness Projection Report

## Scope

更新 `inspect_legacy_hermes_action_migration`，让它识别 Phase186-188 已建立的 Agent approval wrapper：

- `generate_setup` -> `execute_generate_setup_with_approval`
- `generate_storyline` -> `execute_generate_storyline_with_approval`
- `generate_outline` -> `execute_generate_outline_with_approval`

旧 legacy action 的直接执行路由仍保持 `legacy_action_fallback`，因为 slash/dialog 尚未切换到新链路。

## Implementation

- `legacy_hermes_migration_projection.py` 现在从推荐 shape 推导 preview / prepare / execute wrapper 名称。
- 投影会读取 execute wrapper adapter metadata，输出：
  - `migration_stage`
  - `agent_native_execution_route`
  - `approval_wrapper`
- summary 的 `agent_native_ready_count` 现在计入 `agent_native_wrapper_ready`。

## Validation

RED:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "legacy_hermes_migration_projection" -q
# expected 3, got 0 for agent_native_ready_count
```

GREEN / T1:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "legacy_hermes_migration_projection" -q
# 2 passed, 114 deselected

python -m compileall backend/app/services/writing_agent
# exit 0
```

T2:

```powershell
pytest backend/tests/test_writing_agent_tool_aggregation_boundaries.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py -q
# 172 passed

python -m compileall backend/app/services/writing_agent
# exit 0
```

## Novel Progress

本阶段未推进小说正文生成。原因：Phase189 是工具状态投影收敛阶段，解决 Agent 对 Hermes 三个基础生成 wrapper 的可用性认知问题。

## Next Phase

建议 Phase190 聚焦 route projection：

- 让 `inspect_agent_route_preference_projection` 能看到 legacy command 与 Agent approval wrapper 的推荐映射。
- 暂不切换真实 slash/dialog 执行路径，先让 Agent 在只读投影中获得可解释迁移建议。
- 验证不破坏现有 `generate_setup` / `generate_storyline` / `generate_outline` legacy fallback。
