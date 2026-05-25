# Phase65: 世界模型提案决议链路前端动作视图

## 背景

`analyze_chapter_world_model` 之后，Agent 会通过世界模型提案队列来阻止带冲突事实继续进入长篇生成。关键链路是审阅提案、生成决议计划、预览决议影响、在确认后应用决议。当前这些工具缺少 Hermes 对话 action card，用户难以判断 Agent 为什么暂停写作、需要处理多少提案、是否可以继续生成。

## 目标

为以下工具增加前端 action result 投影：

1. `review_world_model_proposals`
2. `plan_world_model_proposal_resolution`
3. `preview_world_model_proposal_resolution`
4. `apply_world_model_proposal_resolution`

## 范围

1. 扩展 `frontend/src/components/chat/agentRunProjection.test.ts`。
2. 扩展 `frontend/src/components/chat/agentRunProjection.ts`。
3. 展示有界摘要：队列状态、待处理提案数、返回条数、高风险数量、批量/个别处理步骤、有效/无效决策、应用数量、剩余待处理数量、是否需要确认、下一步动作数量。
4. 隐藏 raw clusters、resolution steps、decision ids、bundle ids、invalid decision code/detail、applied review ids。

## 非目标

- 不改变后端世界模型提案处理逻辑。
- 不新增世界模型提案详情页。
- 不改变审批/写入确认流程。

## 验证

- TDD RED: `npm run test:unit -- agentRunProjection`
- T0: `npm run test:unit -- agentRunProjection`
- T1: `npm run test:unit -- ChatMessage`
- T1: `npm run build`
- T0: `git diff --check`
