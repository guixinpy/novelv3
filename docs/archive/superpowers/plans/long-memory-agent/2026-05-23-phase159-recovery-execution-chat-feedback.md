# Phase159 Recovery Execution Chat Feedback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用户从 Agent run 抽屉确认执行恢复后，在 Hermes 对话流中追加一条轻量系统反馈，包含新 run 状态和“查看运行”入口。

**Architecture:** 仅追加本地前端反馈，不新增后端消息持久化，不改变恢复执行门禁。`HermesView` 创建执行 run 后调用 chat store 的本地反馈方法；`ChatMessage` 扩展可打开的 Agent run 类型，使 `ui_recovery_execute` 也能复用已有“查看运行”按钮。

**Tech Stack:** Vue 3、Pinia、TypeScript、Vitest。

---

## Files

- Modify: `frontend/src/stores/chat.ts`
  - Add `appendAgentRunExecutionFeedback(run)`.
- Modify: `frontend/src/components/chat/ChatMessage.vue`
  - Allow `ui_recovery_execute` action result messages to expose `查看运行`.
- Modify: `frontend/src/components/chat/ChatMessage.test.ts`
  - Cover recovery execution message opening the run.
- Modify: `frontend/src/views/HermesView.vue`
  - Call the store feedback method after `api.createAgentRun` succeeds.
- Modify: `frontend/src/views/HermesView.test.ts`
  - Assert recovery execution appends a visible chat feedback message.
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase159-recovery-execution-chat-feedback.md`
  - Record validation evidence and next recommendation.

## Success Criteria

- After recovery execution run creation, Hermes chat receives a local system message.
- The message content does not claim business success beyond returned run status.
- The message exposes `查看运行` through existing `ChatMessage` behavior.
- The chat feedback does not include raw `recovery_plan_hash`.
- Existing Phase157 drawer execution behavior remains intact.

## Tasks

### Task 1: Write Failing Tests

- [ ] In `ChatMessage.test.ts`, add a test with `action_result.type: "ui_recovery_execute"` and `data.agent_run_id: "run-executed"`.
- [ ] Assert `[data-testid="open-agent-run"]` exists and emits `openAgentRun` with `run-executed`.
- [ ] In `HermesView.test.ts`, update the `ChatMessageList` stub to render the latest message content.
- [ ] Extend the recovery execution test to assert latest message contains `恢复执行已创建` and does not contain `plan-hash-1`.
- [ ] Run:

```powershell
cd frontend
npm run test:unit -- src/components/chat/ChatMessage.test.ts src/views/HermesView.test.ts
```

Expected: FAIL because `ui_recovery_execute` does not expose `查看运行`, and Hermes does not append feedback.

### Task 2: Implement Local Feedback

- [ ] In `chat.ts`, import `WritingAgentRunDetail`.
- [ ] Add status label/variant helpers for recovery execution messages.
- [ ] Add `appendAgentRunExecutionFeedback(run)`.
- [ ] The method should append:

```ts
{
  role: 'system',
  content: '恢复执行已创建，可在运行详情中查看执行步骤。',
  action_result: {
    type: 'ui_recovery_execute',
    status: run.status,
    data: { agent_run_id: run.id },
  },
  action_result_view: {
    type: 'ui_recovery_execute',
    status: run.status,
    label: '<localized status>',
    variant: '<status variant>',
    detail_items: [
      { label: '运行 ID', value: run.id },
      { label: '状态', value: '<localized status>' },
    ],
  },
  meta: {
    agent_run_id: run.id,
    agent_action_type: 'ui_recovery_execute',
  },
}
```

- [ ] Mark the local history anchor stale after append.

### Task 3: Wire Hermes and ChatMessage

- [ ] In `ChatMessage.vue`, allow `ui_recovery_execute` in the Agent run action-type gate.
- [ ] In `HermesView.vue`, call `chat.appendAgentRunExecutionFeedback(run)` after successful `api.createAgentRun`.
- [ ] Run the targeted tests and verify they pass.

### Task 4: Verification

- [ ] Run:

```powershell
cd frontend
npm run test:unit -- src/components/chat/ChatMessage.test.ts src/components/writingAgent/AgentRunDrawer.test.ts src/views/HermesView.test.ts
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
git add frontend/src/stores/chat.ts frontend/src/components/chat/ChatMessage.vue frontend/src/components/chat/ChatMessage.test.ts frontend/src/views/HermesView.vue frontend/src/views/HermesView.test.ts docs/superpowers/plans/long-memory-agent/2026-05-23-phase159-recovery-execution-chat-feedback.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase159-recovery-execution-chat-feedback.md
git commit -m "feat: show recovery execution feedback in chat"
git push origin main
```
