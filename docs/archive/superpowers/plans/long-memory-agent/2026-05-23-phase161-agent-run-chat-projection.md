# Phase161 Agent Run Chat Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Agent run 相关聊天投影集中到一个前端 helper，为更多 Agent 工具事件进入 Hermes 对话流提供统一入口。

**Architecture:** 新增 `frontend/src/components/chat/agentRunProjection.ts`，集中处理 Agent run action type 判定、run id 提取和恢复执行反馈消息构造。`ChatMessage.vue` 不再内联 action type 列表；`chat.ts` 不再内联恢复执行消息构造细节。

**Tech Stack:** Vue 3、Pinia、TypeScript、Vitest。

---

## Files

- Create: `frontend/src/components/chat/agentRunProjection.ts`
  - Agent run action type allowlist.
  - `getAgentRunIdFromMessage`.
  - `buildAgentRunExecutionFeedback`.
- Create: `frontend/src/components/chat/agentRunProjection.test.ts`
  - Helper behavior coverage.
- Modify: `frontend/src/components/chat/ChatMessage.vue`
  - Use `getAgentRunIdFromMessage`.
- Modify: `frontend/src/stores/chat.ts`
  - Use `buildAgentRunExecutionFeedback`.
- Modify: `frontend/src/components/chat/ChatMessage.test.ts`
  - Existing open-run tests remain as integration coverage.
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase161-agent-run-chat-projection.md`
  - Validation evidence and next recommendation.

## Success Criteria

- Agent run action type allowlist exists in one helper.
- `ChatMessage.vue` delegates run id extraction to the helper.
- `chat.ts` delegates recovery execution feedback construction to the helper.
- Existing behavior for `plan_recovery_tools` and `ui_recovery_execute` remains unchanged.
- Helper tests prove unknown action types do not expose `查看运行` accidentally.

## Tasks

### Task 1: Write Failing Helper Tests

- [ ] Create `frontend/src/components/chat/agentRunProjection.test.ts`.
- [ ] Test `getAgentRunIdFromMessage` returns:
  - `run-preview` for `plan_recovery_tools` action result data.
  - `run-executed` for `ui_recovery_execute` meta.
  - empty string for unknown action type even when `agent_run_id` exists.
- [ ] Test `buildAgentRunExecutionFeedback`:
  - returns system content containing `恢复执行已创建`.
  - includes `action_result.type === "ui_recovery_execute"`.
  - includes `meta.agent_run_id`.
  - does not include `recovery_plan_hash` when serialized.
- [ ] Run:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts
```

Expected: FAIL because the helper does not exist.

### Task 2: Implement Helper

- [ ] Add `agentRunProjection.ts`.
- [ ] Export:

```ts
export const AGENT_RUN_ACTION_TYPES = ['plan_recovery_tools', 'ui_recovery_execute'] as const
export function isAgentRunActionType(value: unknown): boolean
export function getAgentRunIdFromMessage(message: AgentRunMessageLike): string
export function buildAgentRunExecutionFeedback(run: WritingAgentRunDetail): AgentRunFeedbackMessage
```

- [ ] Keep helper structural and independent from Pinia store internals.
- [ ] Run helper tests and verify they pass.

### Task 3: Wire Existing Consumers

- [ ] In `ChatMessage.vue`, replace inline action type check and run id extraction with `getAgentRunIdFromMessage(props.msg)`.
- [ ] In `chat.ts`, remove local recovery execution status helper functions and use `buildAgentRunExecutionFeedback(run)`.
- [ ] Run:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts src/components/chat/ChatMessage.test.ts src/views/HermesView.test.ts
```

Expected: PASS.

### Task 4: Verification

- [ ] Run:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts src/components/chat/ChatMessage.test.ts src/components/writingAgent/AgentRunDrawer.test.ts src/views/HermesView.test.ts
```

- [ ] Run:

```powershell
cd frontend
npm run build
```

- [ ] Run:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

### Task 5: Report, Commit, Push

- [ ] Write the phase report.
- [ ] Commit with:

```powershell
git add frontend/src/components/chat/agentRunProjection.ts frontend/src/components/chat/agentRunProjection.test.ts frontend/src/components/chat/ChatMessage.vue frontend/src/stores/chat.ts docs/superpowers/plans/long-memory-agent/2026-05-23-phase161-agent-run-chat-projection.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase161-agent-run-chat-projection.md
git commit -m "refactor: centralize agent run chat projection"
git push origin main
```
