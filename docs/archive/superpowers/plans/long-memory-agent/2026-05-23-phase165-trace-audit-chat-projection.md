# Phase165 Trace Audit Chat Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将第一个非恢复类 Agent 工具事件 `inspect_agent_trace_audit` 接入前端 Agent run action descriptor registry。

**Architecture:** 扩展 `agentRunProjection.ts` descriptor map，不新增后端行为。`inspect_agent_trace_audit` 是只读 Trace 审计工具，fallback view 从 action result data 的 `audit`、`run`、`failure`、`recommended_actions` 提取安全摘要；`ChatMessage` 继续通过统一 helper 使用 fallback view。

**Tech Stack:** TypeScript、Vue 3、Vitest。

---

## Files

- Modify: `frontend/src/components/chat/agentRunProjection.ts`
  - Register `inspect_agent_trace_audit`.
  - Add trace audit label and detail extraction.
  - Extract run id from `data.agent_run_id` or nested `data.run.id`.
- Modify: `frontend/src/components/chat/agentRunProjection.test.ts`
  - Cover trace audit descriptor, fallback view, and nested run id extraction.
- Modify: `frontend/src/components/chat/ChatMessage.test.ts`
  - Cover trace audit message without backend view rendering Chinese fallback.
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase165-trace-audit-chat-projection.md`
  - Validation evidence and next recommendation.

## Success Criteria

- `inspect_agent_trace_audit` is recognized as an Agent run action type.
- `buildAgentRunActionResultView` returns:
  - label `Trace 审计已生成` for success.
  - variant `success`.
  - detail items for run status, step count, trace count, failure reason, and recommended action count when present.
- `getAgentRunIdFromMessage` can extract nested `data.run.id`.
- `ChatMessage` without backend view renders `Trace 审计已生成`, not raw `inspect_agent_trace_audit`.
- Existing recovery preview/execution behavior remains unchanged.

## Tasks

### Task 1: Write Failing Tests

- [ ] In `agentRunProjection.test.ts`, assert `inspect_agent_trace_audit` is recognized and descriptor exists.
- [ ] Add a fallback view test:

```ts
buildAgentRunActionResultView({
  type: 'inspect_agent_trace_audit',
  status: 'success',
  data: {
    run: { id: 'run-audit-1', status: 'failed' },
    audit: { status: 'failed', step_count: 3, trace_count: 2 },
    failure: { reason_code: 'tool_failed' },
    recommended_actions: [{ tool_name: 'plan_recovery_tools' }],
  },
})
```

- [ ] Assert detail items:
  - `运行状态: 失败`
  - `工具步骤: 3 个`
  - `Trace: 2 条`
  - `失败原因: tool_failed`
  - `建议动作: 1 个`
- [ ] Add run id extraction test for nested `data.run.id`.
- [ ] In `ChatMessage.test.ts`, add a message without backend view and assert Chinese fallback.
- [ ] Run:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts src/components/chat/ChatMessage.test.ts
```

Expected: FAIL because `inspect_agent_trace_audit` is not registered yet.

### Task 2: Implement Descriptor

- [ ] Add `inspect_agent_trace_audit` to `AGENT_RUN_ACTION_TYPES`.
- [ ] Register descriptor with `buildTraceAuditActionResultView`.
- [ ] Add `traceAuditLabel`, `traceAuditDetailItems`, and status/detail label helpers.
- [ ] Extend `getAgentRunIdFromMessage` to read `data.run.id` when `data.agent_run_id` is absent.
- [ ] Run target tests and verify they pass.

### Task 3: Verification

- [ ] Run:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts src/components/chat/ChatMessage.test.ts src/views/HermesView.test.ts
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

### Task 4: Report, Commit, Push

- [ ] Write the phase report.
- [ ] Commit with:

```powershell
git add frontend/src/components/chat/agentRunProjection.ts frontend/src/components/chat/agentRunProjection.test.ts frontend/src/components/chat/ChatMessage.test.ts docs/superpowers/plans/long-memory-agent/2026-05-23-phase165-trace-audit-chat-projection.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase165-trace-audit-chat-projection.md
git commit -m "feat: add trace audit chat projection"
git push origin main
```
