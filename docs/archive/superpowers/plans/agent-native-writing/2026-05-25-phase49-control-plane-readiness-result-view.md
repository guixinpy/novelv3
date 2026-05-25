# Phase49: 控制平面就绪度结果视图

## 背景

Phase48 已让 Agent run API 返回 `agent_control_plane_readiness`。但对话消息的 `action_result_view` 与前端即时运行反馈仍只展示 Agent 身份、工具面和命令契约，用户无法直接看到统一的控制平面状态。

## 目标

在后端对话结果视图和前端 Agent run 反馈中展示控制平面就绪度的中文摘要。

## 范围

1. 后端 `action_result_view` 从 `agent_control_plane_readiness` 生成 detail items。
2. 前端 `agentRunProjection` 生成同样语义的 detail items。
3. 摘要保持有界：只展示状态、总缺口、工具缺口、命令缺口和建议检查数量，不泄露 source 或内部工具 ID。

## 非目标

- 不改 Agent 执行逻辑。
- 不新增新的 API 字段。
- 不做 AgentRunDrawer 展示改造。

## 验证

- T0: `pytest backend/tests/test_dialogs.py -k "agent_control_plane_readiness_detail_items" -q`
- T0: `npm run test -- --run src/components/chat/agentRunProjection.test.ts -t "agent run execution feedback"`
- T0: `git diff --check`
