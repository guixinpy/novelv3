# Phase65: 世界模型提案决议链路前端动作视图

## 目标

补齐世界模型提案处理链路在 Hermes 对话中的结构化展示，让 Agent 暂停写作、等待提案处理、预览/应用决议时具备可审计的中文摘要。

## 变更

1. 在 `frontend/src/components/chat/agentRunProjection.ts` 注册以下 action type：
   - `review_world_model_proposals`
   - `plan_world_model_proposal_resolution`
   - `preview_world_model_proposal_resolution`
   - `apply_world_model_proposal_resolution`
2. 增加四类 action result view：
   - 提案队列报告：队列状态、待处理数量、本次返回、高风险、批量审阅、是否还有更多、建议动作数量。
   - 决议计划：计划状态、待处理数量、处理步骤、高优先级、批量步骤、是否需要确认、下一步工具数量。
   - 决议预览：预览状态、有效/无效决策、预计写入事实、预计解决、预览后剩余、是否需要确认、建议动作数量。
   - 决议应用：应用状态、应用前后待处理数量、已应用、无效决策、是否需要确认、是否可继续生成、建议动作数量。
3. 增加世界模型阻塞状态 variant 映射：
   - `ready/success/completed` -> `success`
   - `blocked/failed/missing_profile` -> `error`
4. 保持 action card 为聚合摘要，不展示 raw clusters、resolution steps、proposal item id、bundle id、invalid decision code/message 或 review id。

## TDD 证据

RED：

```text
npm run test:unit -- agentRunProjection
51 tests | 6 failed
失败点：四个世界模型提案/决议工具未注册，action result view 返回 undefined。
```

GREEN：

```text
npm run test:unit -- agentRunProjection
51 passed
```

## 验证

```text
npm run test:unit -- agentRunProjection
51 passed

npm run test:unit -- ChatMessage
29 passed

npm run build
vue-tsc --noEmit && vite build 成功

git diff --check
通过；仅保留既有 backend/tests/test_writing_agent_runs.py CRLF 警告。
```

## 下一阶段建议

继续补齐修订链路 action card：

1. `plan_chapter_revision`
2. `create_revision_draft`
3. `apply_planner_revision_patch`
4. `expand_chapter_to_target`
5. `compress_chapter_to_target`
