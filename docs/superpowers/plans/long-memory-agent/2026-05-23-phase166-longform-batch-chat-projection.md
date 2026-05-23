# Phase166 Longform Batch Chat Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `inspect_longform_chapter_batch` 接入前端 Agent run action descriptor registry，让长篇批次队列检查结果在聊天中有稳定中文摘要和运行详情入口。

**Architecture:** 只扩展 `frontend/src/components/chat/agentRunProjection.ts` 的 descriptor registry，不改后端工具契约。Fallback view 从后端既有输出 `summary`、`queue`、`selected_task`、`trace` 中提取队列深度、活跃任务、命中任务、章节范围、执行就绪状态等安全摘要；`ChatMessage` 继续复用统一 helper。

**Tech Stack:** TypeScript、Vue 3、Vitest。

---

## Files

- Modify: `frontend/src/components/chat/agentRunProjection.ts`
  - Register `inspect_longform_chapter_batch`.
  - Add batch inspection label and detail extraction.
  - Reuse existing `statusVariant` and `getAgentRunIdFromMessage` behavior for `data.agent_run_id`.
- Modify: `frontend/src/components/chat/agentRunProjection.test.ts`
  - Cover descriptor recognition, fallback view, not-found state, and run id extraction.
- Modify: `frontend/src/components/chat/ChatMessage.test.ts`
  - Cover chat rendering without backend `action_result_view`.
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase166-longform-batch-chat-projection.md`
  - Record validation evidence and next recommendation.

## Backend Contract

`inspect_longform_chapter_batch` returns:

- `status`: `completed`, `not_found`, or `failed`.
- `summary`: `{ total, returned, limit, selected, task_type, by_status }`.
- `queue`: `{ depth, active, terminal, by_status }` when queue inspection completes.
- `tasks`: compact background task list.
- `selected_task`: detailed task or `null`; includes `status`, `chapter_range`, `batch.chapter_indexes`, `resume`, `execution_readiness`.
- `trace`: selected/rejected tool metadata.

## Success Criteria

- `inspect_longform_chapter_batch` is recognized as an Agent run action type.
- `buildAgentRunActionResultView` returns:
  - label `长篇批次检查已生成` for success/completed.
  - label `长篇批次未找到` for backend `not_found`.
  - queue/detail items when present: `队列深度`、`活跃任务`、`命中任务`、`章节范围`、`执行状态`.
- `getAgentRunIdFromMessage` extracts `data.agent_run_id` for this action type.
- `ChatMessage` without backend view renders Chinese fallback, not raw `inspect_longform_chapter_batch`.
- Existing recovery and trace audit projections remain unchanged.

## Tasks

### Task 1: Write Failing Tests

- [x] In `agentRunProjection.test.ts`, assert `inspect_longform_chapter_batch` is recognized and descriptor exists.
- [x] Add run id extraction for:

```ts
{
  action_result: {
    type: 'inspect_longform_chapter_batch',
    status: 'success',
    data: { agent_run_id: 'run-batch-1' },
  },
}
```

- [x] Add a fallback view test:

```ts
buildAgentRunActionResultView({
  type: 'inspect_longform_chapter_batch',
  status: 'success',
  data: {
    status: 'completed',
    summary: { total: 3, returned: 2, selected: true },
    queue: { depth: 2, active: 1, terminal: 1 },
    selected_task: {
      status: 'pending',
      chapter_range: { start: 21, end: 23 },
      execution_readiness: { status: 'materialized_only' },
    },
  },
})
```

- [x] Assert detail items:
  - `队列深度: 2 个`
  - `活跃任务: 1 个`
  - `命中任务: 是`
  - `章节范围: 第21-23章`
  - `执行状态: 已物化，等待执行工具`
- [x] Add a not-found fallback view test with backend data `status: 'not_found'`.
- [x] In `ChatMessage.test.ts`, add a message without backend view and assert Chinese fallback.
- [x] Run:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts src/components/chat/ChatMessage.test.ts
```

Expected: FAIL because `inspect_longform_chapter_batch` is not registered yet.

### Task 2: Implement Descriptor

- [x] Add `inspect_longform_chapter_batch` to `AGENT_RUN_ACTION_TYPES`.
- [x] Register descriptor with `buildLongformBatchActionResultView`.
- [x] Add `longformBatchLabel`, `longformBatchDetailItems`, `chapterRangeLabel`, and `batchExecutionReadinessLabel`.
- [x] Keep output concise and avoid exposing plan hashes.
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
git add frontend/src/components/chat/agentRunProjection.ts frontend/src/components/chat/agentRunProjection.test.ts frontend/src/components/chat/ChatMessage.test.ts docs/superpowers/plans/long-memory-agent/2026-05-23-phase166-longform-batch-chat-projection.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase166-longform-batch-chat-projection.md
git commit -m "feat: add longform batch chat projection"
git push origin main
```
