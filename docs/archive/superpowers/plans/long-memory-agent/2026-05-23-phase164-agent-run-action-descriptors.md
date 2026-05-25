# Phase164 Agent Run Action Descriptors Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Agent run 聊天投影 helper 中的 action type 分支改为 descriptor registry，为后续审稿、检索、世界模型等 Agent 工具事件提供统一扩展点。

**Architecture:** `agentRunProjection.ts` 内部新增 action descriptor map。`isAgentRunActionType`、`getAgentRunIdFromMessage`、`buildAgentRunActionResultView` 都通过 descriptor 查询工作；当前仍只注册 `plan_recovery_tools` 和 `ui_recovery_execute`，不改变用户可见行为。

**Tech Stack:** TypeScript、Vitest。

---

## Files

- Modify: `frontend/src/components/chat/agentRunProjection.ts`
  - Add descriptor type and descriptor registry.
  - Export `getAgentRunActionDescriptor`.
  - Replace direct action type branches with descriptor lookup.
- Modify: `frontend/src/components/chat/agentRunProjection.test.ts`
  - Cover descriptor lookup and unknown descriptor behavior.
  - Cover `ui_recovery_execute` fallback view from action result.
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase164-agent-run-action-descriptors.md`
  - Validation evidence and next recommendation.

## Success Criteria

- `getAgentRunActionDescriptor("plan_recovery_tools")` returns a descriptor.
- `getAgentRunActionDescriptor("ui_recovery_execute")` returns a descriptor.
- Unknown tool/action returns `null`.
- Existing helper behavior is unchanged.
- `ui_recovery_execute` fallback view can be built from action result alone.

## Tasks

### Task 1: Write Failing Tests

- [ ] In `agentRunProjection.test.ts`, add tests for `getAgentRunActionDescriptor`.
- [ ] Add a test for `buildAgentRunActionResultView` with:

```ts
{
  type: 'ui_recovery_execute',
  status: 'running',
  data: { agent_run_id: 'run-running' },
}
```

- [ ] Assert:
  - label `恢复执行中`
  - variant `neutral`
  - detail item `运行 ID: run-running`
- [ ] Run:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts
```

Expected: FAIL because `getAgentRunActionDescriptor` does not exist.

### Task 2: Implement Descriptor Registry

- [ ] Add `AgentRunActionDescriptor`.
- [ ] Add descriptor map for `plan_recovery_tools` and `ui_recovery_execute`.
- [ ] Make `AGENT_RUN_ACTION_TYPES` derive from descriptor keys.
- [ ] Update `isAgentRunActionType`, `getAgentRunIdFromMessage`, and `buildAgentRunActionResultView` to use descriptor lookup.
- [ ] Keep existing private label/detail helpers.
- [ ] Run helper tests and verify they pass.

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
git add frontend/src/components/chat/agentRunProjection.ts frontend/src/components/chat/agentRunProjection.test.ts docs/superpowers/plans/long-memory-agent/2026-05-23-phase164-agent-run-action-descriptors.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase164-agent-run-action-descriptors.md
git commit -m "refactor: add agent run action descriptors"
git push origin main
```
