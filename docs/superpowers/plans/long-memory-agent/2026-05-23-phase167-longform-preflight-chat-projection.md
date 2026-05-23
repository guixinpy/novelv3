# Phase167 Longform Preflight Chat Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `execute_longform_chapter_batch_preflight` 接入前端 Agent run action descriptor registry，让长篇批次预检结果在聊天中显示 ready/blocked 摘要。

**Architecture:** 继续扩展 `agentRunProjection.ts` descriptor map，不改变后端预检流程。Fallback view 从 `checkpoint`、`canonical_execution_plan`、`execution_policy`、`recommended_next_tools` 中提取章节选择、预检状态、就绪/阻塞章节数、停止节点和下一步工具数量；`ChatMessage` 继续通过统一 helper 渲染。

**Tech Stack:** TypeScript、Vue 3、Vitest。

---

## Files

- Modify: `frontend/src/components/chat/agentRunProjection.ts`
  - Register `execute_longform_chapter_batch_preflight`.
  - Add preflight label and detail extraction.
- Modify: `frontend/src/components/chat/agentRunProjection.test.ts`
  - Cover descriptor recognition, ready fallback, blocked fallback, and run id extraction.
- Modify: `frontend/src/components/chat/ChatMessage.test.ts`
  - Cover chat rendering without backend `action_result_view`.
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase167-longform-preflight-chat-projection.md`
  - Record validation evidence and next recommendation.

## Backend Contract

`execute_longform_chapter_batch_preflight` returns:

- `status`: `ready`, `blocked`, `not_found`, or `failed`.
- `task`: selected background task summary.
- `canonical_execution_plan`: includes `chapter_indexes`, `chapters_to_run`, `resume_from_chapter_index`, `stopped_before_node`.
- `checkpoint`: includes `status`, `selected_chapter_indexes`, `ready_chapter_indexes`, `blocked_chapter_indexes`, `generation_started`.
- `execution_policy`: includes `mode`, `requires_confirmation`, `starts_runner`, `high_risk_side_effects_executed`.
- `recommended_next_tools`: next tool names when blocked or after successful preflight.

## Success Criteria

- `execute_longform_chapter_batch_preflight` is recognized as an Agent run action type.
- `buildAgentRunActionResultView` returns:
  - label `长篇批次预检已就绪` for backend `ready`.
  - label `长篇批次预检已阻塞` for backend `blocked`.
  - detail items when present: `预检章节`、`就绪章节`、`阻塞章节`、`停止节点`、`下一步`.
- `getAgentRunIdFromMessage` extracts `data.agent_run_id` for this action type.
- `ChatMessage` without backend view renders Chinese fallback, not raw `execute_longform_chapter_batch_preflight`.
- Existing recovery, trace audit, and longform batch inspection projections remain unchanged.

## Tasks

### Task 1: Write Failing Tests

- [x] In `agentRunProjection.test.ts`, assert `execute_longform_chapter_batch_preflight` is recognized and descriptor exists.
- [x] Add run id extraction for `data.agent_run_id`.
- [x] Add a ready fallback view test:

```ts
buildAgentRunActionResultView({
  type: 'execute_longform_chapter_batch_preflight',
  status: 'success',
  data: {
    status: 'ready',
    canonical_execution_plan: { chapters_to_run: [21], stopped_before_node: 'chapter_generation' },
    checkpoint: {
      status: 'ready',
      selected_chapter_indexes: [21],
      ready_chapter_indexes: [21],
      blocked_chapter_indexes: [],
    },
    recommended_next_tools: ['inspect_longform_chapter_batch'],
  },
})
```

- [x] Assert detail items:
  - `预检章节: 第21章`
  - `就绪章节: 1 章`
  - `阻塞章节: 0 章`
  - `停止节点: 正文生成前`
  - `下一步: 1 个工具`
- [x] Add a blocked fallback view test with `blocked_chapter_indexes: [23]`.
- [x] In `ChatMessage.test.ts`, add a message without backend view and assert Chinese fallback.
- [x] Run:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts src/components/chat/ChatMessage.test.ts
```

Expected: FAIL because `execute_longform_chapter_batch_preflight` is not registered yet.

### Task 2: Implement Descriptor

- [x] Add `execute_longform_chapter_batch_preflight` to `AGENT_RUN_ACTION_TYPES`.
- [x] Register descriptor with `buildLongformPreflightActionResultView`.
- [x] Add `longformPreflightLabel`, `longformPreflightVariant`, `longformPreflightDetailItems`, `chapterIndexesLabel`, and `stoppedBeforeNodeLabel`.
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
git add frontend/src/components/chat/agentRunProjection.ts frontend/src/components/chat/agentRunProjection.test.ts frontend/src/components/chat/ChatMessage.test.ts docs/superpowers/plans/long-memory-agent/2026-05-23-phase167-longform-preflight-chat-projection.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase167-longform-preflight-chat-projection.md
git commit -m "feat: add longform preflight chat projection"
git push origin main
```
