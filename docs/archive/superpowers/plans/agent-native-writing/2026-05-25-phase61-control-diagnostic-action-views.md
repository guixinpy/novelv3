# Phase61: 控制面诊断工具前端动作视图

## 背景

Agent 已具备 `inspect_agent_command_contracts` 与 `inspect_agent_control_plane_readiness` 两个控制面自检工具，但前端 `agentRunProjection` 尚未把它们注册为可识别 action type。Agent 调用后，用户无法在 Hermes 对话里直接看到命令契约缺口、控制平面状态和建议后继工具。

## 目标

为两个控制面诊断工具补齐 action result view：

1. `inspect_agent_command_contracts`
2. `inspect_agent_control_plane_readiness`

## 范围

1. 扩展 `frontend/src/components/chat/agentRunProjection.test.ts`。
2. 扩展 `frontend/src/components/chat/agentRunProjection.ts`。
3. 复用已有命令契约、控制面摘要 helper。
4. 不暴露 raw `commands` / diagnostics 细节，只展示有界摘要。

## 非目标

- 不改变后端诊断工具输出。
- 不新增详情页。
- 不改变 run detail drawer。

## 验证

- TDD RED: `npm run test:unit -- agentRunProjection`
- T0: `npm run test:unit -- agentRunProjection`
- T1: `npm run test:unit -- ChatMessage`
- T1: `npm run build`
- T0: `git diff --check`
