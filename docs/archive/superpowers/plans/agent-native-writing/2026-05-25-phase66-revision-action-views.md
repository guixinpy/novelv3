# Phase66: 章节修订与长度校准前端动作视图

## 背景

审稿和连续性检查发现问题后，Agent 会进入修订链路：生成修订计划、创建修订草稿、应用补丁，或通过扩写/压缩校准章节篇幅。当前这些工具缺少 Hermes 对话 action card，用户无法快速判断 Agent 修了哪一章、修订是否应用、字数是否达标、后续是否需要复审。

## 目标

为以下工具增加前端 action result 投影：

1. `plan_chapter_revision`
2. `create_revision_draft`
3. `apply_planner_revision_patch`
4. `expand_chapter_to_target`
5. `compress_chapter_to_target`

## 范围

1. 扩展 `frontend/src/components/chat/agentRunProjection.test.ts`。
2. 扩展 `frontend/src/components/chat/agentRunProjection.ts`。
3. 展示有界摘要：章节、状态、修订动作数、草稿/修订序号、应用替换数、前后字数、目标字数、警告数、未处理世界模型提案数、是否可继续生成、推荐后续工具数量。
4. 隐藏 raw revision id、chapter id、version id、trace id、replacement payload、failed attempts、正文/摘要长文本。

## 非目标

- 不改变后端修订、扩写或压缩逻辑。
- 不新增修订详情页。
- 不改变 Agent 写入确认流程。

## 验证

- TDD RED: `npm run test:unit -- agentRunProjection`
- T0: `npm run test:unit -- agentRunProjection`
- T1: `npm run test:unit -- ChatMessage`
- T1: `npm run build`
- T0: `git diff --check`
