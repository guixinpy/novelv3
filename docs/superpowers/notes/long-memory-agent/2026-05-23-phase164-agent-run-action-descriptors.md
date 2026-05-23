# Phase164 Agent Run Action Descriptors Report

## Summary

本阶段把 `agentRunProjection` 内部的 action type 分支重构为 descriptor registry。当前仍只注册 `plan_recovery_tools` 和 `ui_recovery_execute`，用户可见行为不变，但后续审稿、检索、世界模型等 Agent 工具事件接入 Hermes 对话层时，可以通过新增 descriptor 扩展。

## Changes

- `frontend/src/components/chat/agentRunProjection.ts`
  - Added `AgentRunActionType`.
  - Added `AgentRunActionDescriptor`.
  - Added internal descriptor map.
  - Added `getAgentRunActionDescriptor`.
  - Updated `isAgentRunActionType` and `buildAgentRunActionResultView` to use descriptor lookup.
- `frontend/src/components/chat/agentRunProjection.test.ts`
  - Added descriptor lookup coverage.
  - Added `ui_recovery_execute` fallback view coverage.

## TDD Evidence

RED command:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts
```

Expected failure:

- `getAgentRunActionDescriptor is not a function`.

GREEN command:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts
```

Result:

- 1 test file passed.
- 8 tests passed.

## Validation

Targeted frontend regression:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts src/components/chat/ChatMessage.test.ts src/views/HermesView.test.ts
```

Result:

- 3 test files passed.
- 28 tests passed.

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

下一阶段可以接入第一个非恢复类 Agent 工具事件 descriptor。建议优先选择只读且已存在的 `inspect_agent_trace_audit` 或 `inspect_longform_chapter_batch`，验证该 registry 能支撑恢复链路以外的 Agent 工具事件投影。
