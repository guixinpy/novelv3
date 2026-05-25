# Phase160 Agent Run Refresh Report

## Summary

本阶段为 Agent 运行详情抽屉增加 `刷新运行` 入口。用户查看恢复执行 run 或其他 Agent run 时，可以直接重新拉取当前 run id 的最新详情，而不需要关闭抽屉再从聊天消息重新打开。

该阶段只增加读路径，不创建新 run，不改变恢复执行策略。

## Changes

- `frontend/src/components/writingAgent/AgentRunDrawer.vue`
  - Added `refresh` emit.
  - Added `刷新运行` button in summary header for loaded run details.
- `frontend/src/views/HermesView.vue`
  - Added `refreshAgentRun()`.
  - Reuses `openAgentRun(activeAgentRunId)` to reload details through existing `api.getAgentRun`.
- Tests
  - `AgentRunDrawer.test.ts` now verifies refresh event emission.
  - `HermesView.test.ts` now verifies drawer refresh calls `api.getAgentRun` again and updates visible run details.

## TDD Evidence

RED command:

```powershell
cd frontend
npm run test:unit -- src/components/writingAgent/AgentRunDrawer.test.ts src/views/HermesView.test.ts
```

Expected failing assertions:

- `AgentRunDrawer`: `[data-testid="refresh-agent-run"]` did not exist.
- `HermesView`: second `api.getAgentRun` call did not happen.

GREEN command:

```powershell
cd frontend
npm run test:unit -- src/components/writingAgent/AgentRunDrawer.test.ts src/views/HermesView.test.ts
```

Result:

- 2 test files passed.
- 10 tests passed.

## Validation

Targeted frontend regression:

```powershell
cd frontend
npm run test:unit -- src/components/chat/ChatMessage.test.ts src/components/writingAgent/AgentRunDrawer.test.ts src/views/HermesView.test.ts
```

Result:

- 3 test files passed.
- 24 tests passed.

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

下一阶段可以开始把 Agent run lifecycle feedback 抽象为统一前端投影：

1. 把 `plan_recovery_tools`、`ui_recovery_execute` 等 run-related action 的中文标签、详情项和 open-run 判定集中到一个 helper。
2. 降低 `ChatMessage.vue` 和 `chat.ts` 中对具体 action type 的硬编码。
3. 为后续更多 Agent 工具调用事件进入 Hermes 对话层打基础。
