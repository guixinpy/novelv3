# Phase68: Agent 诊断动作投影模块拆分

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Trace、任务队列、健康、命令契约、控制平面、记忆与知识库路由诊断的 action result view 从 `agentRunProjection.ts` 拆到独立模块。

**Architecture:** `agentRunProjection.ts` 保持聚合入口；新增 `agentDiagnosticRunProjection.ts` 负责 Agent 基础设施诊断工具的 descriptors 与 view builders。该模块用私有 helper 生成有界摘要，不暴露 raw diagnostics、sources、commands、issues。

**Tech Stack:** Vue/Vitest/TypeScript。

---

## 任务

- [ ] 新增失败测试：`agentRunProjection.test.ts` 导入 `DIAGNOSTIC_AGENT_RUN_ACTION_TYPES` 与 `DIAGNOSTIC_AGENT_RUN_ACTION_DESCRIPTORS`，断言 7 个诊断工具类型与 descriptor。
- [ ] 运行 `npm run test:unit -- agentRunProjection`，预期因模块不存在或导出缺失失败。
- [ ] 新增 `frontend/src/components/chat/agentDiagnosticRunProjection.ts`，迁移 Trace、Job、Health、Command Contract、Control Plane、Memory Route、Knowledge Base Route 的 action view。
- [ ] 修改 `frontend/src/components/chat/agentRunProjection.ts`，聚合诊断模块的 action types 和 descriptors，移除已迁移的本地 view builder 与诊断细节函数。
- [ ] 运行 `npm run test:unit -- agentRunProjection`，预期通过。
- [ ] 运行 `npm run test:unit -- ChatMessage`、`npm run build`、`git diff --check`。
- [ ] 新增阶段报告。
