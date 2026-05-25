# Phase159 Recovery Execution Chat Feedback Report

## Summary

本阶段把恢复执行入口接回 Hermes 对话层。用户在 Agent run 抽屉中点击 `确认执行恢复` 并成功创建新的 execution run 后，聊天流会追加一条本地系统反馈，显示恢复执行 run 的状态，并复用已有 `查看运行` 入口。

该反馈是前端本地消息，不新增后端持久化，不改变恢复执行门禁。

## Changes

- `frontend/src/stores/chat.ts`
  - Added `appendAgentRunExecutionFeedback(run)`.
  - Added localized status label and variant helpers for recovery execution messages.
  - Local message includes run id and status only; it does not expose `recovery_plan_hash`.
- `frontend/src/components/chat/ChatMessage.vue`
  - Allows `ui_recovery_execute` action results to show `查看运行`.
- `frontend/src/views/HermesView.vue`
  - Calls `chat.appendAgentRunExecutionFeedback(run)` after `api.createAgentRun` succeeds.
- Tests
  - Added ChatMessage coverage for `ui_recovery_execute`.
  - Extended Hermes recovery execution test to assert chat feedback appears and excludes raw plan hash.

## TDD Evidence

RED command:

```powershell
cd frontend
npm run test:unit -- src/components/chat/ChatMessage.test.ts src/views/HermesView.test.ts
```

Expected failing assertions:

- `ChatMessage`: no `[data-testid="open-agent-run"]` for `ui_recovery_execute`.
- `HermesView`: latest chat message remained the greeting and did not contain `恢复执行已创建`.

GREEN command:

```powershell
cd frontend
npm run test:unit -- src/components/chat/ChatMessage.test.ts src/views/HermesView.test.ts
```

Result:

- 2 test files passed.
- 18 tests passed.

## Validation

Targeted frontend regression:

```powershell
cd frontend
npm run test:unit -- src/components/chat/ChatMessage.test.ts src/components/writingAgent/AgentRunDrawer.test.ts src/views/HermesView.test.ts
```

Result:

- 3 test files passed.
- 23 tests passed.

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

下一阶段建议继续把恢复执行反馈从本地消息推进到可追踪状态：

1. 如果 `ui_recovery_execute` run 关联后台任务，前端应显示执行中状态并允许用户刷新详情。
2. 若执行 run 失败，Hermes 反馈应显示后端错误摘要和下一步恢复建议。
3. 中期应考虑把这类 Agent run lifecycle feedback 统一为工具调用事件，而不是每个入口各自拼本地消息。
