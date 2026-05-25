# Phase64: 审稿与世界模型工具前端动作视图

## 背景

Agent 化后的长篇写作链路会频繁调用 `review_chapter_quality`、`review_chapter_continuity` 与 `analyze_chapter_world_model`。这些工具是生成后质量闸门和世界模型入库前置分析的核心，但在 Hermes 对话中缺少结构化 action card 时，用户只能看到原始结果或无法快速判断 Agent 的下一步依据。

## 目标

为以下工具增加前端 action result 投影：

1. `review_chapter_quality`
2. `review_chapter_continuity`
3. `analyze_chapter_world_model`

## 范围

1. 扩展 `frontend/src/components/chat/agentRunProjection.test.ts`。
2. 扩展 `frontend/src/components/chat/agentRunProjection.ts`。
3. 展示有界摘要：章节、审查状态、评分、问题数量、回看窗口、世界模型提案数量、推荐后续工具数量。
4. 使用中文状态标签，避免在对话卡片中暴露 raw issue code、proposal 详情或 bundle/hash 类内部标识。

## 非目标

- 不改变后端审稿/世界模型工具输出。
- 不新增审稿或世界模型详情页。
- 不改变长篇批次模块的投影逻辑。

## 验证

- TDD RED: `npm run test:unit -- agentRunProjection`
- T0: `npm run test:unit -- agentRunProjection`
- T1: `npm run test:unit -- ChatMessage`
- T1: `npm run build`
- T0: `git diff --check`
