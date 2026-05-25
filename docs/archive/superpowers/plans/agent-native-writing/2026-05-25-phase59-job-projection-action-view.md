# Phase59: Job Projection 前端动作视图

## 背景

`inspect_agent_job_projection` 已成为 Agent 观察长篇批处理、章节任务占用、恢复建议和控制面健康度的核心工具。但前端 `agentRunProjection` 尚未把它注册为可识别 action type，Hermes 对话中无法稳定展示任务队列投影摘要。

## 目标

为 `inspect_agent_job_projection` 增加 action result view，展示队列深度、活跃任务数、选中任务状态、下一章、关联 Agent run 数、控制面缺口、命令契约缺口与推荐工具数量。

## 范围

1. `frontend/src/components/chat/agentRunProjection.test.ts`
   - 覆盖 action type 识别。
   - 覆盖 descriptor 注册。
   - 覆盖 action card detail items。
2. `frontend/src/components/chat/agentRunProjection.ts`
   - 注册 `inspect_agent_job_projection`。
   - 新增 job projection view builder。
   - 复用控制面与命令契约摘要 helper，不暴露 raw payload。

## 非目标

- 不改后端 Job projection 输出。
- 不新增完整任务队列页面。
- 不改变 AgentRunDrawer。

## 验证

- TDD RED: `npm run test:unit -- agentRunProjection`
- T0: `npm run test:unit -- agentRunProjection`
- T1: `npm run build`
- T0: `git diff --check`
