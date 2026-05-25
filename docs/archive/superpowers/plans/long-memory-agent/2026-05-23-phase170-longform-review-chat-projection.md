# Phase170 Longform Review Chat Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `review_longform_chapter_batch_execution` 接入前端 Agent run action descriptor registry，让长篇批次执行后审查结果在聊天中显示通过、阻塞与已跳过摘要。

**Architecture:** 继续扩展 `agentRunProjection.ts` descriptor map，不改变后端审查流程。Fallback view 从 `chapter_index`、`review_gate`、`reviews`、`side_effects`、`recommended_next_tools` 和 `reason` 中提取审查章节、闸门状态、阻塞/警告数量、质量/连续性/世界模型状态和下一步工具数量。

**Tech Stack:** TypeScript、Vue 3、Vitest。

---

## Files

- Modify: `frontend/src/components/chat/agentRunProjection.ts`
  - Register `review_longform_chapter_batch_execution`.
  - Add post-generation review label and detail extraction.
- Modify: `frontend/src/components/chat/agentRunProjection.test.ts`
  - Cover descriptor recognition, completed fallback, blocked fallback, skipped fallback, and run id extraction.
- Modify: `frontend/src/components/chat/ChatMessage.test.ts`
  - Cover chat rendering without backend `action_result_view`.
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase170-longform-review-chat-projection.md`
  - Record validation evidence and next recommendation.

## Backend Contract

`review_longform_chapter_batch_execution` returns:

- `status`: `completed`, `blocked`, `skipped`, `not_found`, or `failed`.
- `chapter_index` on reviewable outputs.
- `review_gate`: includes `status`, `blocker_count`, `warning_count`, `decision`, `recommended_actions`.
- `reviews`: includes `quality`, `continuity`, and `world_model`.
- `side_effects`: includes executed/skipped review tools.
- `recommended_next_tools`: follow-up tools for revision or next batch.
- `reason`: blocked or skipped reason.

## Success Criteria

- `review_longform_chapter_batch_execution` is recognized as an Agent run action type.
- `buildAgentRunActionResultView` returns:
  - label `长篇批次审查已通过` for backend `completed`.
  - label `长篇批次审查已阻塞` for backend `blocked`.
  - label `长篇批次审查已记录` for backend `skipped`.
  - detail items when present: `审查章节`、`审查闸门`、`阻塞项`、`警告项`、`质量审查`、`连续性审查`、`世界模型`、`下一步`.
- `getAgentRunIdFromMessage` extracts `data.agent_run_id` for this action type.
- `ChatMessage` without backend view renders Chinese fallback, not raw `review_longform_chapter_batch_execution`.
- Existing recovery, trace audit, batch inspection, preflight, prepare, and execute projections remain unchanged.

## Tasks

### Task 1: Write Failing Tests

- [x] In `agentRunProjection.test.ts`, assert `review_longform_chapter_batch_execution` is recognized and descriptor exists.
- [x] Add run id extraction for `data.agent_run_id`.
- [x] Add a completed fallback view test:

```ts
buildAgentRunActionResultView({
  type: 'review_longform_chapter_batch_execution',
  status: 'success',
  data: {
    status: 'completed',
    chapter_index: 21,
    review_gate: { status: 'passed', blocker_count: 0, warning_count: 1 },
    reviews: {
      quality: { status: 'ready' },
      continuity: { status: 'ready' },
      world_model: { status: 'completed' },
    },
    recommended_next_tools: ['inspect_longform_chapter_batch', 'prepare_longform_chapter_batch_execution'],
  },
})
```

- [x] Assert detail items:
  - `审查章节: 第21章`
  - `审查闸门: 已通过`
  - `阻塞项: 0 项`
  - `警告项: 1 项`
  - `质量审查: 就绪`
  - `连续性审查: 就绪`
  - `世界模型: 成功`
  - `下一步: 2 个工具`
- [x] Add blocked fallback view test with `reason: 'post_generation_review_has_blockers'`.
- [x] Add skipped fallback view test with `reason: 'post_generation_review_already_recorded'`.
- [x] In `ChatMessage.test.ts`, add a message without backend view and assert Chinese fallback.
- [x] Run:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts src/components/chat/ChatMessage.test.ts
```

Expected: FAIL because `review_longform_chapter_batch_execution` is not registered yet.

### Task 2: Implement Descriptor

- [x] Add `review_longform_chapter_batch_execution` to `AGENT_RUN_ACTION_TYPES`.
- [x] Register descriptor with `buildLongformReviewActionResultView`.
- [x] Add `longformReviewLabel`, `longformReviewVariant`, `longformReviewDetailItems`, and review label helpers.
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
git add frontend/src/components/chat/agentRunProjection.ts frontend/src/components/chat/agentRunProjection.test.ts frontend/src/components/chat/ChatMessage.test.ts docs/superpowers/plans/long-memory-agent/2026-05-23-phase170-longform-review-chat-projection.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase170-longform-review-chat-projection.md
git commit -m "feat: add longform review chat projection"
git push origin main
```
