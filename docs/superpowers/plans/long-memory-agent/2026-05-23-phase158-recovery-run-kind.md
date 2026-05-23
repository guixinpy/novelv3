# Phase158 Recovery Run Kind Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Agent 运行详情抽屉中明确标识恢复预览 run 与恢复执行 run，减少用户对 Phase157 执行入口的误读。

**Architecture:** 只读 UI 增强，不改变后端执行逻辑。通过 `run.entrypoint`、`run.input.execute_recovery`、`run.input.recovery_run_id` 和 `plan_recovery_tools` 预览输出推导运行类型，并在摘要区/恢复策略区展示稳定中文标签。

**Tech Stack:** Vue 3、TypeScript、Vitest。

---

## Files

- Modify: `frontend/src/components/writingAgent/AgentRunDrawer.vue`
  - Add run kind label and recovery execution source metadata.
- Modify: `frontend/src/components/writingAgent/AgentRunDrawer.test.ts`
  - Cover preview run label and execution run label.
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase158-recovery-run-kind.md`
  - Record validation evidence and next recommendation.

## Success Criteria

- A run containing `plan_recovery_tools` preview output is labeled `恢复预览` in the summary.
- A run with `entrypoint: "ui_recovery_execute"` or `input.execute_recovery === true` is labeled `恢复执行` in the summary.
- Execution runs display `来源运行` and `计划哈希` when those values exist in `run.input`.
- This phase does not add any new write path or backend behavior.

## Tasks

### Task 1: Write Failing Drawer Tests

- [ ] Extend the existing recovery policy test to assert the summary contains:

```text
运行类型
恢复预览
```

- [ ] Add a new execution-run test with:

```ts
entrypoint: 'ui_recovery_execute',
input: {
  execute_recovery: true,
  recovery_run_id: 'source-run-1',
  recovery_plan_hash: 'plan-hash-1',
}
```

- [ ] Assert the summary contains:

```text
运行类型
恢复执行
来源运行
source-run-1
计划哈希
plan-hash-1
```

- [ ] Run:

```powershell
cd frontend
npm run test:unit -- src/components/writingAgent/AgentRunDrawer.test.ts
```

Expected: FAIL because the drawer does not show run kind or execution metadata.

### Task 2: Implement Read-Only Labels

- [ ] Add a computed `runKindLabel`.
- [ ] Add computed values for `recoverySourceRunId` and `recoveryPlanHash`.
- [ ] Add `运行类型` to summary facts.
- [ ] Add a small metadata section for execution-source values when present.
- [ ] Run the drawer test file and verify it passes.

### Task 3: Verification

- [ ] Run targeted drawer tests:

```powershell
cd frontend
npm run test:unit -- src/components/writingAgent/AgentRunDrawer.test.ts
```

- [ ] Run frontend build:

```powershell
cd frontend
npm run build
```

- [ ] Run hygiene:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

### Task 4: Report, Commit, Push

- [ ] Write the phase report.
- [ ] Commit with:

```powershell
git add frontend/src/components/writingAgent/AgentRunDrawer.vue frontend/src/components/writingAgent/AgentRunDrawer.test.ts docs/superpowers/plans/long-memory-agent/2026-05-23-phase158-recovery-run-kind.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase158-recovery-run-kind.md
git commit -m "feat: label recovery agent run kind"
git push origin main
```
