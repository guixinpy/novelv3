# Phase169 Longform Execute Chat Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `execute_longform_chapter_batch` 接入前端 Agent run action descriptor registry，让长篇批次真实执行结果在聊天中显示完成、阻塞与失败摘要。

**Architecture:** 继续扩展 `agentRunProjection.ts` descriptor map，不改变后端执行流程。Fallback view 从 `chapter_index`、`executed_chapter_indexes`、`generation`、`evidence`、`agent_plan_approval_verification`、`execution_resource_binding`、`side_effects`、`recommended_next_tools` 中提取章节执行、生成状态、证据状态、审批校验、资源绑定和下一步工具数量；避免暴露 attempt/approval hash。

**Tech Stack:** TypeScript、Vue 3、Vitest。

---

## Files

- Modify: `frontend/src/components/chat/agentRunProjection.ts`
  - Register `execute_longform_chapter_batch`.
  - Add execution label and detail extraction.
- Modify: `frontend/src/components/chat/agentRunProjection.test.ts`
  - Cover descriptor recognition, completed fallback, blocked fallback, failed fallback, and run id extraction.
- Modify: `frontend/src/components/chat/ChatMessage.test.ts`
  - Cover chat rendering without backend `action_result_view`.
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase169-longform-execute-chat-projection.md`
  - Record validation evidence and next recommendation.

## Backend Contract

`execute_longform_chapter_batch` returns:

- `status`: `completed`, `blocked`, `failed`, `not_found`, or request-level failure.
- `chapter_index` and `executed_chapter_indexes` on success.
- `generation`: model/action execution result.
- `evidence`: includes `chapter_content_written`, `task_progress_checkpoint_updated`, `execution_checkpoint_written`, `agent_plan_approval_verified`, `trace_id`.
- `agent_plan_approval_verification`: includes `status`.
- `execution_resource_binding`: includes `status`.
- `side_effects`: includes executed/skipped/inherited/failed.
- `recommended_next_tools`: quality, continuity, world model, and inspect follow-up tools.
- `reason` for blocked outputs; `error` for failed outputs.

## Success Criteria

- `execute_longform_chapter_batch` is recognized as an Agent run action type.
- `buildAgentRunActionResultView` returns:
  - label `长篇批次执行已完成` for backend `completed`.
  - label `长篇批次执行已阻塞` for backend `blocked`.
  - label `长篇批次执行失败` for backend `failed`.
  - detail items when present: `执行章节`、`生成状态`、`章节写入`、`审批校验`、`资源绑定`、`副作用`、`下一步`.
- `getAgentRunIdFromMessage` extracts `data.agent_run_id` for this action type.
- `ChatMessage` without backend view renders Chinese fallback, not raw `execute_longform_chapter_batch`.
- Existing recovery, trace audit, batch inspection, preflight, and prepare projections remain unchanged.

## Tasks

### Task 1: Write Failing Tests

- [x] In `agentRunProjection.test.ts`, assert `execute_longform_chapter_batch` is recognized and descriptor exists.
- [x] Add run id extraction for `data.agent_run_id`.
- [x] Add a completed fallback view test:

```ts
buildAgentRunActionResultView({
  type: 'execute_longform_chapter_batch',
  status: 'success',
  data: {
    status: 'completed',
    chapter_index: 21,
    executed_chapter_indexes: [21],
    generation: { status: 'success' },
    evidence: {
      chapter_content_written: true,
      agent_plan_approval_verified: true,
    },
    execution_resource_binding: { status: 'ready' },
    side_effects: { executed: ['generate_chapter', 'background_task_result_execution_checkpoint'] },
    recommended_next_tools: ['review_chapter_quality', 'review_chapter_continuity'],
  },
})
```

- [x] Assert detail items:
  - `执行章节: 第21章`
  - `生成状态: 成功`
  - `章节写入: 已写入`
  - `审批校验: 已验证`
  - `资源绑定: 就绪`
  - `副作用: 2 项`
  - `下一步: 2 个工具`
- [x] Add blocked fallback view test with `reason: 'confirmation_required'`.
- [x] Add failed fallback view test with `error: 'generate_chapter failed'`.
- [x] In `ChatMessage.test.ts`, add a message without backend view and assert Chinese fallback.
- [x] Run:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts src/components/chat/ChatMessage.test.ts
```

Expected: FAIL because `execute_longform_chapter_batch` is not registered yet.

### Task 2: Implement Descriptor

- [x] Add `execute_longform_chapter_batch` to `AGENT_RUN_ACTION_TYPES`.
- [x] Register descriptor with `buildLongformExecuteActionResultView`.
- [x] Add `longformExecuteLabel`, `longformExecuteVariant`, `longformExecuteDetailItems`, and status label helpers.
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
git add frontend/src/components/chat/agentRunProjection.ts frontend/src/components/chat/agentRunProjection.test.ts frontend/src/components/chat/ChatMessage.test.ts docs/superpowers/plans/long-memory-agent/2026-05-23-phase169-longform-execute-chat-projection.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase169-longform-execute-chat-projection.md
git commit -m "feat: add longform execute chat projection"
git push origin main
```
