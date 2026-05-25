# Phase162 Recovery Execution Error Feedback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 当恢复执行 run 返回失败或阻止状态时，Hermes 本地反馈展示后端错误摘要，帮助用户理解下一步恢复方向。

**Architecture:** 只扩展 Phase161 的 `agentRunProjection` helper，不改后端，不新增写路径。错误摘要来自 `WritingAgentRunDetail.error`，作为 `action_result_view.detail_items` 的安全中文详情项展示；不暴露 recovery plan hash 或内部 input。

**Tech Stack:** TypeScript、Vitest。

---

## Files

- Modify: `frontend/src/components/chat/agentRunProjection.ts`
  - Add error summary detail item for failed/blocked execution runs.
- Modify: `frontend/src/components/chat/agentRunProjection.test.ts`
  - Cover failed execution feedback with error summary and no plan hash leakage.
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase162-recovery-execution-error-feedback.md`
  - Validation evidence and next recommendation.

## Success Criteria

- `buildAgentRunExecutionFeedback` adds `错误摘要` when `run.error` is a non-empty string.
- Failed execution feedback uses `variant: "error"`.
- Error summary is trimmed.
- Serialized feedback does not include `recovery_plan_hash`.
- Existing success feedback remains unchanged.

## Tasks

### Task 1: Write Failing Helper Test

- [ ] Add a test to `agentRunProjection.test.ts` for a failed `ui_recovery_execute` run:

```ts
{
  id: 'run-failed',
  status: 'failed',
  error: ' 工具执行失败：缺少章节上下文 ',
  input: { recovery_plan_hash: 'plan-hash-2' },
}
```

- [ ] Assert:
  - `action_result_view.variant === "error"`.
  - `action_result_view.label === "恢复执行失败"`.
  - detail items include `{ label: "错误摘要", value: "工具执行失败：缺少章节上下文" }`.
  - serialized message does not include `plan-hash-2`.
- [ ] Run:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts
```

Expected: FAIL because error summary is not yet included.

### Task 2: Implement Error Detail

- [ ] In `agentRunProjection.ts`, add a helper to trim `run.error`.
- [ ] Append `{ label: "错误摘要", value: error }` to detail items when error exists.
- [ ] Keep plan hash excluded by not reading `run.input`.
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
git add frontend/src/components/chat/agentRunProjection.ts frontend/src/components/chat/agentRunProjection.test.ts docs/superpowers/plans/long-memory-agent/2026-05-23-phase162-recovery-execution-error-feedback.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase162-recovery-execution-error-feedback.md
git commit -m "feat: show recovery execution error summaries"
git push origin main
```
