# Phase66: 章节修订与长度校准前端动作视图

## 目标

让 Agent 在审稿后进入修订、补丁应用、扩写和压缩链路时，Hermes 对话能展示可审计中文摘要，而不是暴露内部修订 ID、版本 ID、替换 payload 或长文本。

## 变更

1. 在 `frontend/src/components/chat/agentRunProjection.ts` 注册以下 action type：
   - `plan_chapter_revision`
   - `create_revision_draft`
   - `apply_planner_revision_patch`
   - `expand_chapter_to_target`
   - `compress_chapter_to_target`
2. 增加五类 action result view：
   - 修订计划：章节、计划状态、修订动作数、世界模型提案压力、下一步工具数量。
   - 修订草稿：章节、草稿状态、修订序号、批注数、修正数、修订动作数、下一步工具数量。
   - 补丁应用：章节、应用状态、修订序号、替换数量、当前字数、是否可继续生成、下一步工具数量。
   - 章节扩写：章节、扩写状态、原字数、当前字数、目标下限、警告数、世界模型提案数、是否可继续生成、下一步工具数量。
   - 章节压缩：章节、压缩状态、原字数、当前字数、目标上限、禁用词剩余、重试次数、失败尝试次数、世界模型提案数、是否可继续生成、下一步工具数量。
3. 增加修订状态中文标签与 variant 映射：
   - `drafted` -> `已起草`
   - `warning` -> `有警告`
   - `completed/success` -> `成功`
   - `blocked/failed` -> error variant
4. 卡片只展示聚合摘要，不展示 revision id、chapter id、version id、trace id、raw replacement、failed attempt、plan findings 或 change summary。

## TDD 证据

RED：

```text
npm run test:unit -- agentRunProjection
56 tests | 7 failed
失败点：五个修订/长度校准工具未注册，action result view 返回 undefined。
```

GREEN：

```text
npm run test:unit -- agentRunProjection
56 passed
```

## 验证

```text
npm run test:unit -- agentRunProjection
56 passed

npm run test:unit -- ChatMessage
29 passed

npm run build
vue-tsc --noEmit && vite build 成功

git diff --check
通过；仅保留既有 backend/tests/test_writing_agent_runs.py CRLF 警告。
```

## 下一阶段建议

继续收敛 `agentRunProjection.ts` 的增长风险：把审稿/世界模型/修订工具 action view 拆到独立模块，类似已有的 `longformAgentRunProjection.ts`，避免 Agent 工具面继续扩展时单文件过大。
