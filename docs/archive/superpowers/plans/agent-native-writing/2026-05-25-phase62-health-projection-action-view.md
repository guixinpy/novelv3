# Phase62: Agent 健康投影前端动作视图

## 背景

`inspect_agent_health_projection` 是 Agent 自检入口，会聚合控制平面、命令契约、profile policy、Trace audit 与推荐工具。但前端 action result 尚未注册该工具，导致 Agent 调用健康投影后用户无法在对话中直接看到健康状态摘要。

## 目标

为 `inspect_agent_health_projection` 增加 Hermes action card，展示 Agent 健康状态、控制面摘要、命令契约摘要、profile policy issue 数、诊断数和推荐工具数。

## 范围

1. 扩展 `frontend/src/components/chat/agentRunProjection.test.ts`。
2. 扩展 `frontend/src/components/chat/agentRunProjection.ts`。
3. 复用已有控制面与命令契约摘要 helper。
4. 不暴露 raw diagnostics / profile policy issues / delegate edges。

## 非目标

- 不改变后端健康投影输出。
- 不新增独立健康详情页。
- 不改变 `/status` 命令已有展示。

## 验证

- TDD RED: `npm run test:unit -- agentRunProjection`
- T0: `npm run test:unit -- agentRunProjection`
- T1: `npm run test:unit -- ChatMessage`
- T1: `npm run build`
- T0: `git diff --check`
