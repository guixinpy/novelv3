# Phase64: 审稿与世界模型工具前端动作视图

## 目标

让 Hermes 对话能结构化展示 Agent 调用审稿与世界模型分析工具后的结果，减少 raw JSON/内部诊断泄漏，并让用户快速判断质量闸门、连续性闸门和世界模型入库前置分析状态。

## 变更

1. 在 `frontend/src/components/chat/agentRunProjection.ts` 注册以下 action type：
   - `review_chapter_quality`
   - `review_chapter_continuity`
   - `analyze_chapter_world_model`
2. 增加三个 action result view：
   - 章节质量审查：章节、审查状态、评分、问题数量、建议动作数量。
   - 章节连续性审查：章节、审查状态、回看窗口、问题数量、建议动作数量。
   - 世界模型分析：章节、分析状态、提案数量、下一步工具数量。
3. 增加中文状态标签与 variant 映射：
   - `needs_revision` -> `需修订`
   - `needs_attention` -> `需处理`
   - `completed/success` -> `成功`
4. 卡片只展示聚合计数，不展示 raw issue code、issue detail、proposal 内容、proposal bundle id。

## TDD 证据

RED：

```text
npm run test:unit -- agentRunProjection
47 tests | 5 failed
失败点：工具未注册，三个 action result view 返回 undefined。
```

GREEN：

```text
npm run test:unit -- agentRunProjection
47 passed
```

## 验证

```text
npm run test:unit -- agentRunProjection
47 passed

npm run test:unit -- ChatMessage
29 passed

npm run build
vue-tsc --noEmit && vite build 成功

git diff --check
通过；仅保留既有 backend/tests/test_writing_agent_runs.py CRLF 警告。
```

## 下一阶段建议

继续补齐世界模型提案审阅与修订类工具的对话投影，例如：

1. `review_world_model_proposals`
2. `plan_world_model_proposal_resolution`
3. `preview_world_model_proposal_resolution`
4. `apply_world_model_proposal_resolution`
5. `plan_chapter_revision`
6. `create_revision_draft`
