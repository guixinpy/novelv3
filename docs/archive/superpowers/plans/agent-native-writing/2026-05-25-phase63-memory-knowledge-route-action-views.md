# Phase63: 记忆与知识库路由前端动作视图

## 背景

长期记忆 Agent 的关键能力包括 `inspect_agent_memory_route` 与 `inspect_agent_knowledge_base_route`。这两个工具已经能诊断长篇记忆、检索覆盖、知识库稀疏度、作者偏好和学习规则，但前端 action result 未注册，Agent 调用结果无法在 Hermes 对话中形成可读摘要。

## 目标

为以下工具增加 action card：

1. `inspect_agent_memory_route`
2. `inspect_agent_knowledge_base_route`

## 范围

1. 扩展 `frontend/src/components/chat/agentRunProjection.test.ts`。
2. 扩展 `frontend/src/components/chat/agentRunProjection.ts`。
3. 展示有界摘要：路由状态、章节记忆覆盖、检索文档数、知识库状态、学习规则数量、候选知识数量、来源数量、诊断项和推荐工具数量。
4. 不暴露 raw learned rules、knowledge candidates、sources 或 diagnostics 详情。

## 非目标

- 不改变后端路由工具输出。
- 不新增知识库/记忆详情页。
- 不改变 AgentRunDrawer。

## 验证

- TDD RED: `npm run test:unit -- agentRunProjection`
- T0: `npm run test:unit -- agentRunProjection`
- T1: `npm run test:unit -- ChatMessage`
- T1: `npm run build`
- T0: `git diff --check`
