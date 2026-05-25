# Phase67: 写作工具动作投影模块拆分

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将审稿、世界模型、修订与长度校准工具的 action result view 从 `agentRunProjection.ts` 拆到独立写作工具投影模块。

**Architecture:** `agentRunProjection.ts` 保持对外聚合入口和现有 API；新增 `writingToolAgentRunProjection.ts` 负责 `review_chapter_*`、`analyze_chapter_world_model`、世界模型提案决议、章节修订/扩写/压缩工具的 descriptors 与 view builders。现有测试继续验证聚合入口，同时增加模块边界测试。

**Tech Stack:** Vue/Vitest/TypeScript。

---

## 任务

- [ ] 新增失败测试：`agentRunProjection.test.ts` 导入 `WRITING_TOOL_AGENT_RUN_ACTION_TYPES` 与 `WRITING_TOOL_AGENT_RUN_ACTION_DESCRIPTORS`，断言写作工具模块导出 12 个工具类型与对应 descriptor。
- [ ] 运行 `npm run test:unit -- agentRunProjection`，预期因模块不存在或导出缺失失败。
- [ ] 新增 `frontend/src/components/chat/writingToolAgentRunProjection.ts`，迁移 Phase64-66 中新增的写作工具 action view builder 与私有 helper。
- [ ] 修改 `frontend/src/components/chat/agentRunProjection.ts`，用 `...WRITING_TOOL_AGENT_RUN_ACTION_TYPES` 和 `...WRITING_TOOL_AGENT_RUN_ACTION_DESCRIPTORS` 聚合写作工具投影，移除已迁移的本地 builder/helper。
- [ ] 运行 `npm run test:unit -- agentRunProjection`，预期通过。
- [ ] 运行 `npm run test:unit -- ChatMessage`、`npm run build`、`git diff --check`。
- [ ] 新增阶段报告，记录拆分范围、验证结果和下一阶段建议。
