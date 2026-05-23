# Phase157 Recovery Execute CTA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Agent 运行详情抽屉中，为后端已判定可执行的恢复预览提供显式确认执行入口，并通过既有 hash + confirm 门禁创建新的执行 run。

**Architecture:** 不新增后端执行策略，不绕过 `plan_recovery_tools` 的 `can_execute`、`execution_policy.status`、`source_run_id` 和 `plan_hash`。前端只在预览满足可执行条件时显示按钮，点击后由 Hermes 调用 `POST /projects/{id}/agent-runs` 创建 `ui_recovery_execute` run。

**Tech Stack:** Vue 3、TypeScript、Vitest、FastAPI 既有 Writing Agent run API。

---

## Files

- Modify: `frontend/src/api/types.ts`
  - Add create-run request types for frontend API contract.
- Modify: `frontend/src/api/client.ts`
  - Add `createAgentRun(projectId, data)`.
- Modify: `frontend/src/components/writingAgent/AgentRunDrawer.vue`
  - Compute recovery execution readiness and emit `executeRecovery`.
- Modify: `frontend/src/components/writingAgent/AgentRunDrawer.test.ts`
  - Cover executable and blocked recovery policy states.
- Modify: `frontend/src/views/HermesView.vue`
  - Handle drawer execution event and create confirmed recovery run.
- Modify: `frontend/src/views/HermesView.test.ts`
  - Cover API payload and drawer update after execution.
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase157-recovery-execute-cta.md`
  - Record validation evidence and follow-up risk.

## Success Criteria

- `AgentRunDrawer` 不可执行预览只展示策略和阻止原因，不显示执行按钮。
- `AgentRunDrawer` 可执行预览显示 `确认执行恢复`，并 emit `{ sourceRunId, planHash }`。
- `HermesView` 点击执行后调用 `api.createAgentRun(projectId, payload)`，payload 必须包含：
  - `entrypoint: "ui_recovery_execute"`
  - `input.auto_plan: true`
  - `input.recovery_run_id`
  - `input.execute_recovery: true`
  - `input.confirm_execute: true`
  - `input.recovery_plan_hash`
- 点击后抽屉切换到新建执行 run 的详情。
- 后端既有恢复执行门禁测试仍通过。

## Tasks

### Task 1: Write Failing Frontend Tests

- [ ] Add an `AgentRunDrawer` test where `plan_recovery_tools` output contains `can_execute: true`, `source_run_id`, `plan_hash`, and `execution_policy.status: "ready"`.
- [ ] Assert the drawer renders `确认执行恢复`.
- [ ] Click the button and assert `executeRecovery` emits `{ sourceRunId, planHash }`.
- [ ] Extend the existing blocked-policy test to assert the execute button is absent.
- [ ] Add a `HermesView` test where the drawer stub emits `executeRecovery`.
- [ ] Assert `api.createAgentRun` receives the confirmed recovery payload and the drawer shows the returned run id.
- [ ] Run:

```powershell
npm run test:unit -- src/components/writingAgent/AgentRunDrawer.test.ts src/views/HermesView.test.ts
```

Expected: FAIL because the button, event, API method, and Hermes handler do not exist yet.

### Task 2: Implement Drawer Readiness and Event

- [ ] In `AgentRunDrawer.vue`, add an emit signature:

```ts
executeRecovery: [payload: { sourceRunId: string; planHash: string }]
```

- [ ] Add computed readiness from `recoveryPreview.can_execute`, `executionPolicy.status`, `source_run_id`, and `plan_hash`.
- [ ] Render `确认执行恢复` only when readiness is true.
- [ ] Keep blocked previews read-only.
- [ ] Run the drawer test file and verify the drawer tests pass.

### Task 3: Implement API Types and Hermes Handler

- [ ] Add `WritingAgentToolRequest` and `WritingAgentRunCreate` to `frontend/src/api/types.ts`.
- [ ] Add `api.createAgentRun`.
- [ ] In `HermesView.vue`, add `executeRecoveryFromRun(payload)`:

```ts
await api.createAgentRun(pid.value, {
  goal: '执行恢复计划',
  entrypoint: 'ui_recovery_execute',
  input: {
    auto_plan: true,
    recovery_run_id: payload.sourceRunId,
    execute_recovery: true,
    confirm_execute: true,
    recovery_plan_hash: payload.planHash,
  },
})
```

- [ ] Bind `@execute-recovery="executeRecoveryFromRun"` on `AgentRunDrawer`.
- [ ] After success, show the returned run in the drawer.
- [ ] Run the Hermes test file and verify it passes.

### Task 4: Verification

- [ ] Run targeted frontend tests:

```powershell
npm run test:unit -- src/components/writingAgent/AgentRunDrawer.test.ts src/views/HermesView.test.ts
```

- [ ] Run targeted backend recovery contract tests:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_auto_plan_previews_recovery_tool_plan_by_default backend\tests\test_writing_agent_runs.py::test_agent_run_auto_plan_executes_recovery_after_hash_confirmation backend\tests\test_writing_agent_runs.py::test_agent_run_auto_plan_rejects_recovery_execute_hash_mismatch -q
```

- [ ] Run build:

```powershell
npm run build
```

- [ ] Run hygiene:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

### Task 5: Report, Commit, Push

- [ ] Write the phase report with changed behavior, validation evidence, and next recommendation.
- [ ] Commit with:

```powershell
git add frontend/src/api/types.ts frontend/src/api/client.ts frontend/src/components/writingAgent/AgentRunDrawer.vue frontend/src/components/writingAgent/AgentRunDrawer.test.ts frontend/src/views/HermesView.vue frontend/src/views/HermesView.test.ts docs/superpowers/plans/long-memory-agent/2026-05-23-phase157-recovery-execute-cta.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase157-recovery-execute-cta.md
git commit -m "feat: execute recovery from agent run drawer"
git push origin main
```
