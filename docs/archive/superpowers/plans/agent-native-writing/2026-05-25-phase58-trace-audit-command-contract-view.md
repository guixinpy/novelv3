# Phase58: Trace Audit 命令契约前端视图

## 背景

Phase57 已让 `inspect_agent_trace_audit` 返回 `command_contracts` 摘要，但 Hermes 对话里的 Trace audit action card 仍只显示运行状态、步骤数、Trace 数、失败原因和建议动作数量。用户无法从卡片直接看到 `/` 命令迁移到 Agent 控制面的契约缺口。

## 目标

让 Trace audit action result view 展示命令契约摘要，包括命令契约是否已投影、Agent 控制命令数量和契约缺口数量。

## 范围

1. 扩展 `frontend/src/components/chat/agentRunProjection.test.ts`。
2. 扩展 `frontend/src/components/chat/agentRunProjection.ts`。
3. 复用 run detail 已有命令契约展示语义，避免暴露 `source` 或原始 `commands`。

## 非目标

- 不新增新的 action type。
- 不调整后端 API。
- 不改变 AgentRunDrawer 展示。

## 验证

- TDD RED: `npm run test:unit -- agentRunProjection`
- T0: `npm run test:unit -- agentRunProjection`
- T0: `git diff --check`
