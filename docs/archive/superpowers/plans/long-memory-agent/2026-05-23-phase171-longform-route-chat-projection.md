# Phase171 Longform Route Chat Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `route_longform_chapter_batch_after_review` 接入前端 Agent run action descriptor registry，让审查后路由结果在聊天中显示继续下一批、进入修订、阻塞与已记录摘要。

**Architecture:** 继续扩展 `agentRunProjection.ts` descriptor map，不改变后端路由流程。Fallback view 从 `route_decision`、`recovery_plan`、`next_batch_plan`、`recommended_next_tools` 和 `reason` 中提取路由章节、路由决策、下一章、下一批、修订动作和下一步工具数量。

**Tech Stack:** TypeScript、Vue 3、Vitest。

---

## Files

- Modify: `frontend/src/components/chat/agentRunProjection.ts`
  - Register `route_longform_chapter_batch_after_review`.
  - Add post-review route label and detail extraction.
- Modify: `frontend/src/components/chat/agentRunProjection.test.ts`
  - Cover descriptor recognition, continue route fallback, revision route fallback, blocked fallback, and run id extraction.
- Modify: `frontend/src/components/chat/ChatMessage.test.ts`
  - Cover chat rendering without backend `action_result_view`.
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase171-longform-route-chat-projection.md`
  - Record validation evidence and next recommendation.

## Backend Contract

`route_longform_chapter_batch_after_review` returns:

- `status`: `completed`, `blocked`, `skipped`, `not_found`, or `failed`.
- `chapter_index`: reviewed/executed chapter.
- `route_decision`: includes `decision`, `status`, `should_generate_next_chapter`, `next_chapter_index`, and `next_batch_size`.
- `recovery_plan`: present for revision route.
- `next_batch_plan`: present for continue route.
- `recommended_next_tools`: next tool names.
- `reason`: blocked or skipped reason.

## Success Criteria

- `route_longform_chapter_batch_after_review` is recognized as an Agent run action type.
- `buildAgentRunActionResultView` returns:
  - label `长篇批次已路由到下一批` for completed `continue_to_next_batch`.
  - label `长篇批次已路由到修订` for completed `stop_for_revision`.
  - label `长篇批次路由已阻塞` for backend `blocked`.
  - label `长篇批次路由已记录` for backend `skipped`.
  - detail items when present: `路由章节`、`路由决策`、`下一章`、`下一批`、`修订动作`、`下一步`.
- `getAgentRunIdFromMessage` extracts `data.agent_run_id` for this action type.
- `ChatMessage` without backend view renders Chinese fallback, not raw `route_longform_chapter_batch_after_review`.
- Existing recovery, trace audit, batch inspection, preflight, prepare, execute, and review projections remain unchanged.

## Tasks

### Task 1: Write Failing Tests

- [x] In `agentRunProjection.test.ts`, assert `route_longform_chapter_batch_after_review` is recognized and descriptor exists.
- [x] Add run id extraction for `data.agent_run_id`.
- [x] Add a continue route fallback view test:

```ts
buildAgentRunActionResultView({
  type: 'route_longform_chapter_batch_after_review',
  status: 'success',
  data: {
    status: 'completed',
    chapter_index: 21,
    route_decision: {
      decision: 'continue_to_next_batch',
      next_chapter_index: 22,
      next_batch_size: 2,
    },
    next_batch_plan: { batch: { chapter_indexes: [22, 23] } },
    recommended_next_tools: ['enqueue_longform_chapter_batch', 'inspect_longform_chapter_batch'],
  },
})
```

- [x] Assert detail items:
  - `路由章节: 第21章`
  - `路由决策: 继续下一批`
  - `下一章: 第22章`
  - `下一批: 第22-23章`
  - `下一步: 2 个工具`
- [x] Add a revision route fallback view test with `decision: 'stop_for_revision'`.
- [x] Add a blocked fallback view test with `reason: 'missing_post_generation_review_result'`.
- [x] In `ChatMessage.test.ts`, add a message without backend view and assert Chinese fallback.
- [x] Run:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts src/components/chat/ChatMessage.test.ts
```

Expected: FAIL because `route_longform_chapter_batch_after_review` is not registered yet.

### Task 2: Implement Descriptor

- [x] Add `route_longform_chapter_batch_after_review` to `AGENT_RUN_ACTION_TYPES`.
- [x] Register descriptor with `buildLongformRouteActionResultView`.
- [x] Add `longformRouteLabel`, `longformRouteVariant`, `longformRouteDetailItems`, and route decision label helpers.
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
git add frontend/src/components/chat/agentRunProjection.ts frontend/src/components/chat/agentRunProjection.test.ts frontend/src/components/chat/ChatMessage.test.ts docs/superpowers/plans/long-memory-agent/2026-05-23-phase171-longform-route-chat-projection.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase171-longform-route-chat-projection.md
git commit -m "feat: add longform route chat projection"
git push origin main
```
