# Phase163 Recovery Preview View Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 当前端收到 `plan_recovery_tools` action result 但缺少后端 `action_result_view` 时，仍能通过统一 helper 显示稳定中文投影。

**Architecture:** 扩展 Phase161 的 `agentRunProjection`，新增 `buildAgentRunActionResultView(actionResult)`。`ChatMessage.vue` 优先使用后端 `action_result_view`，缺失时用 helper 为 Agent run action 生成 fallback view；非 Agent run action 继续走原有通用 fallback。

**Tech Stack:** Vue 3、TypeScript、Vitest。

---

## Files

- Modify: `frontend/src/components/chat/agentRunProjection.ts`
  - Add `buildAgentRunActionResultView`.
  - Add recovery preview status/detail labels.
- Modify: `frontend/src/components/chat/agentRunProjection.test.ts`
  - Cover `plan_recovery_tools` fallback view and unknown action return.
- Modify: `frontend/src/components/chat/ChatMessage.vue`
  - Use projected Agent run view when backend view is missing.
- Modify: `frontend/src/components/chat/ChatMessage.test.ts`
  - Cover recovery preview message without `action_result_view`.
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase163-recovery-preview-view-fallback.md`
  - Validation evidence and next recommendation.

## Success Criteria

- `buildAgentRunActionResultView` returns `null` for unknown action types.
- `plan_recovery_tools + success` returns label `恢复预览已生成` and `variant: "success"`.
- Recovery preview fallback details include source run, recovery status, execution policy, and recovery tool count when present.
- `ChatMessage` without backend `action_result_view` does not display raw `plan_recovery_tools`.
- Existing backend-projected labels still take precedence.

## Tasks

### Task 1: Write Failing Tests

- [ ] In `agentRunProjection.test.ts`, add a test for:

```ts
buildAgentRunActionResultView({
  type: 'plan_recovery_tools',
  status: 'success',
  data: {
    source_run_id: 'source-run-123456',
    recovery: { status: 'recommended' },
    execution_policy: { status: 'ready' },
    tools: [{ tool_name: 'prepare_generate_chapter_execution' }],
  },
})
```

- [ ] Assert label, variant, and detail items:
  - `来源运行: source-r`
  - `恢复状态: 建议恢复`
  - `执行策略: 可执行`
  - `恢复工具: 1 个`
- [ ] Assert unknown action returns `null`.
- [ ] In `ChatMessage.test.ts`, add a recovery preview message without `action_result_view`.
- [ ] Assert it renders `恢复预览已生成`, `执行策略`, and does not render `plan_recovery_tools`.
- [ ] Run:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts src/components/chat/ChatMessage.test.ts
```

Expected: FAIL because the helper function and ChatMessage fallback are not implemented.

### Task 2: Implement Fallback Projection

- [ ] Add `buildAgentRunActionResultView` to `agentRunProjection.ts`.
- [ ] Reuse `isAgentRunActionType`.
- [ ] Add private helpers for:
  - status variant
  - recovery preview label
  - recovery status label
  - execution policy label
  - detail item extraction
- [ ] Keep detail extraction read-only and avoid raw hashes.
- [ ] Run helper tests and verify they pass.

### Task 3: Wire ChatMessage

- [ ] Import `buildAgentRunActionResultView`.
- [ ] Add computed `projectedActionResultView`.
- [ ] Use it in `resultText`, `resultVariant`, and `resultDetailItems`.
- [ ] Run ChatMessage tests and verify they pass.

### Task 4: Verification

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

### Task 5: Report, Commit, Push

- [ ] Write the phase report.
- [ ] Commit with:

```powershell
git add frontend/src/components/chat/agentRunProjection.ts frontend/src/components/chat/agentRunProjection.test.ts frontend/src/components/chat/ChatMessage.vue frontend/src/components/chat/ChatMessage.test.ts docs/superpowers/plans/long-memory-agent/2026-05-23-phase163-recovery-preview-view-fallback.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase163-recovery-preview-view-fallback.md
git commit -m "feat: add recovery preview chat fallback"
git push origin main
```
