# Phase168 Longform Prepare Chat Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `prepare_longform_chapter_batch_execution` 接入前端 Agent run action descriptor registry，让长篇批次执行准备结果在聊天中显示审批与阻塞摘要。

**Architecture:** 继续扩展 `agentRunProjection.ts` descriptor map，不改变后端执行准备流程。Fallback view 从 `attempt_manifest`、`approval_contract`、`agent_plan_approval_contract`、`side_effects`、`recommended_next_tools` 中提取章节范围、审批状态、写入步骤数、高风险副作用和下一步工具数量；`ChatMessage` 继续通过统一 helper 渲染。

**Tech Stack:** TypeScript、Vue 3、Vitest。

---

## Files

- Modify: `frontend/src/components/chat/agentRunProjection.ts`
  - Register `prepare_longform_chapter_batch_execution`.
  - Add execution prepare label and detail extraction.
- Modify: `frontend/src/components/chat/agentRunProjection.test.ts`
  - Cover descriptor recognition, approval-required fallback, blocked fallback, and run id extraction.
- Modify: `frontend/src/components/chat/ChatMessage.test.ts`
  - Cover chat rendering without backend `action_result_view`.
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase168-longform-prepare-chat-projection.md`
  - Record validation evidence and next recommendation.

## Backend Contract

`prepare_longform_chapter_batch_execution` returns:

- `status`: `approval_required`, `blocked`, `not_found`, or `failed`.
- `task`: selected background task summary.
- `attempt_manifest`: includes `chapter_indexes`, `stopped_before_node`, `execution_steps`.
- `approval_contract`: includes `consume_tool`, `required_confirmation`, `high_risk_side_effects`.
- `agent_plan_approval_contract`: includes `status` and `write_step_count`.
- `side_effects`: lists executed/skipped/blocked high-risk operations.
- `recommended_next_tools`: next tool names.
- `reason`: blocked reason when preparation cannot proceed.

## Success Criteria

- `prepare_longform_chapter_batch_execution` is recognized as an Agent run action type.
- `buildAgentRunActionResultView` returns:
  - label `长篇批次执行准备待确认` for backend `approval_required`.
  - label `长篇批次执行准备已阻塞` for backend `blocked`.
  - detail items when present: `执行章节`、`审批状态`、`写入步骤`、`消费工具`、`高风险副作用`、`下一步`.
- `getAgentRunIdFromMessage` extracts `data.agent_run_id` for this action type.
- `ChatMessage` without backend view renders Chinese fallback, not raw `prepare_longform_chapter_batch_execution`.
- Existing recovery, trace audit, batch inspection, and preflight projections remain unchanged.

## Tasks

### Task 1: Write Failing Tests

- [x] In `agentRunProjection.test.ts`, assert `prepare_longform_chapter_batch_execution` is recognized and descriptor exists.
- [x] Add run id extraction for `data.agent_run_id`.
- [x] Add an approval-required fallback view test:

```ts
buildAgentRunActionResultView({
  type: 'prepare_longform_chapter_batch_execution',
  status: 'success',
  data: {
    status: 'approval_required',
    attempt_manifest: {
      chapter_indexes: [21],
      stopped_before_node: 'chapter_generation',
      execution_steps: [{ tool_name: 'generate_chapter' }],
    },
    approval_contract: {
      consume_tool: 'execute_longform_chapter_batch',
      high_risk_side_effects: ['chapter_generation', 'world_model_intake'],
    },
    agent_plan_approval_contract: { status: 'requires_confirmation', write_step_count: 1 },
    recommended_next_tools: ['execute_longform_chapter_batch'],
  },
})
```

- [x] Assert detail items:
  - `执行章节: 第21章`
  - `审批状态: 等待确认`
  - `写入步骤: 1 个`
  - `消费工具: execute_longform_chapter_batch`
  - `高风险副作用: 2 项`
  - `下一步: 1 个工具`
- [x] Add a blocked fallback view test with `reason: 'missing_ready_preflight_checkpoint'`.
- [x] In `ChatMessage.test.ts`, add a message without backend view and assert Chinese fallback.
- [x] Run:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts src/components/chat/ChatMessage.test.ts
```

Expected: FAIL because `prepare_longform_chapter_batch_execution` is not registered yet.

### Task 2: Implement Descriptor

- [x] Add `prepare_longform_chapter_batch_execution` to `AGENT_RUN_ACTION_TYPES`.
- [x] Register descriptor with `buildLongformPrepareActionResultView`.
- [x] Add `longformPrepareLabel`, `longformPrepareVariant`, `longformPrepareDetailItems`, and `approvalStatusLabel`.
- [x] Keep output concise and avoid exposing hashes.
- [x] Run target tests and verify they pass.

### Task 3: Verification

- [x] Run:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts src/components/chat/ChatMessage.test.ts src/views/HermesView.test.ts
```

- [x] Run:

```powershell
cd frontend
npm run build
```

- [x] Run:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

### Task 4: Report, Commit, Push

- [x] Write the phase report.
- [ ] Commit with:

```powershell
git add frontend/src/components/chat/agentRunProjection.ts frontend/src/components/chat/agentRunProjection.test.ts frontend/src/components/chat/ChatMessage.test.ts docs/superpowers/plans/long-memory-agent/2026-05-23-phase168-longform-prepare-chat-projection.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase168-longform-prepare-chat-projection.md
git commit -m "feat: add longform prepare chat projection"
git push origin main
```
