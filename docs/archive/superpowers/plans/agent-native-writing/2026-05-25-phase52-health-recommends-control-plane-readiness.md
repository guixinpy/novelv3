# Phase52: 健康投影推荐统一控制面检查

## 背景

健康投影已经包含 `control_plane_readiness`，但当工具契约或命令契约存在缺口时，`recommended_tools` 仍只推荐底层契约检查工具。对 Agent 来说，统一控制面检查更适合作为第一入口。

## 目标

当健康投影发现工具契约或命令契约缺口时，在 `recommended_tools` 中优先加入 `inspect_agent_control_plane_readiness`，再保留底层诊断工具。

## 范围

1. 更新健康投影推荐工具映射。
2. 补充命令契约缺口测试，确保统一控制面检查被推荐。

## 非目标

- 不新增诊断 code。
- 不改变健康状态判定。
- 不改变 `control_plane_readiness` 输出结构。

## 验证

- T0: `pytest backend/tests/test_writing_agent_health_projection.py -k "command_contract_gap" -q`
- T0: `pytest backend/tests/test_writing_agent_tool_executor.py -k "health_and_route_diagnosis_tools" -q`
- T0: `git diff --check`
