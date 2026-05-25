# Phase160 Agent Run Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Agent 运行详情抽屉中提供显式刷新入口，使恢复执行 run 和其他 Agent run 的生命周期状态可重新拉取。

**Architecture:** 前端只增加 read-through refresh，不新增写路径。`AgentRunDrawer` 发出 `refresh` 事件；`HermesView` 复用当前 `activeAgentRunId` 调用既有 `api.getAgentRun`，并用返回结果替换抽屉详情。

**Tech Stack:** Vue 3、TypeScript、Vitest。

---

## Files

- Modify: `frontend/src/components/writingAgent/AgentRunDrawer.vue`
  - Add `refresh` emit and a `刷新运行` button when a run exists.
- Modify: `frontend/src/components/writingAgent/AgentRunDrawer.test.ts`
  - Cover refresh event emission.
- Modify: `frontend/src/views/HermesView.vue`
  - Add `refreshAgentRun`.
- Modify: `frontend/src/views/HermesView.test.ts`
  - Cover drawer refresh calling `api.getAgentRun` again and updating the visible run.
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase160-agent-run-refresh.md`
  - Record validation evidence and next recommendation.

## Success Criteria

- Drawer displays `刷新运行` for loaded run details.
- Clicking `刷新运行` emits `refresh`.
- Hermes handles refresh by reloading the active run id with `api.getAgentRun`.
- Refresh does not create new runs and does not mutate chat messages.
- Existing recovery execute flow remains intact.

## Tasks

### Task 1: Write Failing Tests

- [ ] In `AgentRunDrawer.test.ts`, assert loaded run detail renders `[data-testid="refresh-agent-run"]`.
- [ ] Click it and assert emitted `refresh`.
- [ ] In `HermesView.test.ts`, update the drawer stub to emit `refresh`.
- [ ] Add a test that:
  - opens run `run-1`,
  - changes `api.getAgentRun` next response to `run-1-refreshed`,
  - clicks refresh,
  - asserts `api.getAgentRun` was called twice with `project-1`, `run-1`,
  - asserts drawer text contains `run-1-refreshed`.
- [ ] Run:

```powershell
cd frontend
npm run test:unit -- src/components/writingAgent/AgentRunDrawer.test.ts src/views/HermesView.test.ts
```

Expected: FAIL because refresh UI and handler do not exist yet.

### Task 2: Implement Refresh Event and Handler

- [ ] Add `refresh: []` to `AgentRunDrawer` emits.
- [ ] Add a button with `data-testid="refresh-agent-run"` in the summary area.
- [ ] Add `refreshAgentRun()` in `HermesView.vue`; it should no-op without `activeAgentRunId`.
- [ ] Bind `@refresh="refreshAgentRun"` on `AgentRunDrawer`.
- [ ] Run the targeted tests and verify they pass.

### Task 3: Verification

- [ ] Run:

```powershell
cd frontend
npm run test:unit -- src/components/writingAgent/AgentRunDrawer.test.ts src/views/HermesView.test.ts
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
git add frontend/src/components/writingAgent/AgentRunDrawer.vue frontend/src/components/writingAgent/AgentRunDrawer.test.ts frontend/src/views/HermesView.vue frontend/src/views/HermesView.test.ts docs/superpowers/plans/long-memory-agent/2026-05-23-phase160-agent-run-refresh.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase160-agent-run-refresh.md
git commit -m "feat: refresh agent run details"
git push origin main
```
