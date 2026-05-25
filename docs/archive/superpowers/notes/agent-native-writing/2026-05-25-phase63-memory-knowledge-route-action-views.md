# Phase63 报告：记忆与知识库路由前端动作视图

## 目标

让 `inspect_agent_memory_route` 与 `inspect_agent_knowledge_base_route` 在 Hermes 对话中具备可读 action card，补齐长期记忆 Agent 的记忆/知识库路由反馈链。

## 变更

1. `frontend/src/components/chat/agentRunProjection.ts`
   - 注册 `inspect_agent_memory_route`。
   - 注册 `inspect_agent_knowledge_base_route`。
   - 新增记忆路由 action view。
   - 新增知识库路由 action view。
   - 新增通用 `routeStatusLabel()`、`memoryProvenanceDetailItems()` 与 `diagnosticAndRecommendationItems()`。
   - 只展示覆盖度与数量摘要，不泄漏 raw learned rules、knowledge candidates、sources 或 diagnostics 细节。
2. `frontend/src/components/chat/agentRunProjection.test.ts`
   - 覆盖 action type 识别。
   - 覆盖 descriptor 注册。
   - 覆盖记忆路由卡片：路由状态、章节记忆、长篇记忆、检索文档、记忆溯源、来源数量、诊断项、推荐工具。
   - 覆盖知识库路由卡片：路由状态、作者偏好、学习规则、本次返回、知识候选、记忆溯源、来源数量、诊断项、推荐工具。
   - 验证不会泄漏具体来源、规则、候选标题或诊断 code。

## 验证

TDD RED：

```powershell
npm run test:unit -- agentRunProjection
# failed: inspect_agent_memory_route / inspect_agent_knowledge_base_route 未注册，action view 为 undefined
```

GREEN / 回归：

```powershell
npm run test:unit -- agentRunProjection
# 44 passed

npm run test:unit -- ChatMessage
# 29 passed

npm run build
# vue-tsc --noEmit && vite build succeeded

git diff --check
# pass; existing warning only: backend/tests/test_writing_agent_runs.py CRLF will be replaced by LF
```

## 结论

Phase63 补齐了长期记忆与知识库路由工具的对话展示层。Agent 现在可以在对话中诊断长篇记忆、检索覆盖、作者偏好、学习规则和知识候选，并把结果以可读摘要反馈给用户。
