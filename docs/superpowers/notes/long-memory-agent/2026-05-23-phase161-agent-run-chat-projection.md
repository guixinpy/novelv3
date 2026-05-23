# Phase161 Agent Run Chat Projection Report

## Summary

本阶段把 Agent run 相关聊天投影集中到 `agentRunProjection` helper。此前 `ChatMessage.vue` 内联 action type allowlist，`chat.ts` 内联恢复执行反馈消息构造；现在这些逻辑收口到一个可测试模块，为后续更多 Agent 工具调用事件进入 Hermes 对话层打基础。

该阶段不新增业务写路径，只做前端投影重构。

## Changes

- `frontend/src/components/chat/agentRunProjection.ts`
  - Added `AGENT_RUN_ACTION_TYPES`.
  - Added `isAgentRunActionType`.
  - Added `getAgentRunIdFromMessage`.
  - Added `buildAgentRunExecutionFeedback`.
- `frontend/src/components/chat/agentRunProjection.test.ts`
  - Covers supported action type extraction.
  - Covers unknown action type hiding run id.
  - Covers recovery execution feedback construction without leaking plan hash.
- `frontend/src/components/chat/ChatMessage.vue`
  - Delegates Agent run id extraction to `getAgentRunIdFromMessage`.
- `frontend/src/stores/chat.ts`
  - Delegates recovery execution feedback construction to `buildAgentRunExecutionFeedback`.

## TDD Evidence

RED command:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts
```

Expected failure:

- Test suite failed because `./agentRunProjection` did not exist.

GREEN command:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts src/components/chat/ChatMessage.test.ts src/views/HermesView.test.ts
```

Result:

- 3 test files passed.
- 22 tests passed.

## Validation

Targeted frontend regression:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts src/components/chat/ChatMessage.test.ts src/components/writingAgent/AgentRunDrawer.test.ts src/views/HermesView.test.ts
```

Result:

- 4 test files passed.
- 27 tests passed.

Build:

```powershell
cd frontend
npm run build
```

Result: `vue-tsc --noEmit` and `vite build` passed.

Hygiene:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

Result:

- `git diff --check`: passed.
- secret scan: no matches.

## Next Recommendation

下一阶段可以继续把 Agent run lifecycle 事件抽象为更完整的“前端事件投影层”：

1. 支持 execution run 失败态携带后端错误摘要。
2. 将 `plan_recovery_tools` 的 action result view 也纳入 helper 统一构造。
3. 为后续审稿、检索、世界模型等 Agent 工具事件提供同一套 chat projection contract。
