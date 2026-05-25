# Phase163 Recovery Preview View Fallback Report

## Summary

本阶段为 `plan_recovery_tools` 增加前端 fallback 投影。若 Hermes 收到恢复预览 action result 但缺少后端 `action_result_view`，`ChatMessage` 会通过 `agentRunProjection` 生成稳定中文标签和详情，不再退回 raw `plan_recovery_tools`。

该阶段不改变后端投影；后端 `action_result_view` 仍优先。

## Changes

- `frontend/src/components/chat/agentRunProjection.ts`
  - Added `buildAgentRunActionResultView`.
  - Added recovery preview fallback label and detail projection.
  - Added detail labels for source run, recovery status, execution policy, and tool count.
- `frontend/src/components/chat/ChatMessage.vue`
  - Added `projectedActionResultView`.
  - Uses backend view first, helper fallback second.
- `frontend/src/components/chat/agentRunProjection.test.ts`
  - Covers recovery preview fallback view.
  - Covers unknown action result returning `null`.
- `frontend/src/components/chat/ChatMessage.test.ts`
  - Covers recovery preview message without backend view.

## TDD Evidence

RED command:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts src/components/chat/ChatMessage.test.ts
```

Expected failures:

- `buildAgentRunActionResultView is not a function`.
- `ChatMessage` rendered raw `plan_recovery_tools` instead of `恢复预览已生成`.

GREEN command:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts src/components/chat/ChatMessage.test.ts
```

Result:

- 2 test files passed.
- 21 tests passed.

## Validation

Targeted frontend regression:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts src/components/chat/ChatMessage.test.ts src/views/HermesView.test.ts
```

Result:

- 3 test files passed.
- 26 tests passed.

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

下一阶段建议继续把 Agent run action projection 从 “恢复链路专用” 扩展到更通用的 contract：

1. 将工具事件的 label/detail schema 明确成前端类型。
2. 为未来审稿、检索、世界模型工具事件添加同样的 fallback 投影测试。
3. 中期可将后端 `action_result_view.py` 与前端 helper 的 label contract 对齐成共享文档，降低双端漂移。
