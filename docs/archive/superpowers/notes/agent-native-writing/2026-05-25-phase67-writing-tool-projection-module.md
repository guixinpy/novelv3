# Phase67: 写作工具动作投影模块拆分

## 目标

降低 `frontend/src/components/chat/agentRunProjection.ts` 的增长风险，把审稿、世界模型、修订与长度校准工具的 action result view 迁到独立模块，同时保持聚合入口 API 与现有行为不变。

## 变更

1. 新增 `frontend/src/components/chat/writingToolAgentRunProjection.ts`。
2. 新模块导出：
   - `WRITING_TOOL_AGENT_RUN_ACTION_TYPES`
   - `WRITING_TOOL_AGENT_RUN_ACTION_DESCRIPTORS`
3. 覆盖 12 个写作工具：
   - `review_chapter_quality`
   - `review_chapter_continuity`
   - `analyze_chapter_world_model`
   - `review_world_model_proposals`
   - `plan_world_model_proposal_resolution`
   - `preview_world_model_proposal_resolution`
   - `apply_world_model_proposal_resolution`
   - `plan_chapter_revision`
   - `create_revision_draft`
   - `apply_planner_revision_patch`
   - `expand_chapter_to_target`
   - `compress_chapter_to_target`
4. `agentRunProjection.ts` 改为聚合 `WRITING_TOOL_AGENT_RUN_ACTION_TYPES` 与 `WRITING_TOOL_AGENT_RUN_ACTION_DESCRIPTORS`。
5. `agentRunProjection.ts` 从 1707 行降到 1041 行；新增写作工具模块 704 行。

## TDD 证据

RED：

```text
npm run test:unit -- agentRunProjection
Failed to load url ./writingToolAgentRunProjection
```

GREEN：

```text
npm run test:unit -- agentRunProjection
57 passed
```

## 验证

```text
npm run test:unit -- agentRunProjection
57 passed

npm run test:unit -- ChatMessage
29 passed

npm run build
vue-tsc --noEmit && vite build 成功

git diff --check
通过；仅保留既有 backend/tests/test_writing_agent_runs.py CRLF 警告。
```

## 下一阶段建议

继续拆分 `agentRunProjection.ts` 中的控制平面、记忆/知识库、Trace/Job 投影，或者进一步把 `writingToolAgentRunProjection.ts` 拆成 `review`、`worldModel`、`revision` 三个模块。
