# Phase172 Longform Projection Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将长篇批次 Agent run action projection 从 `agentRunProjection.ts` 拆到独立模块，降低后续 Agent 工具投影继续扩展时的维护成本。

**Architecture:** 新增 `frontend/src/components/chat/longformAgentRunProjection.ts`，承载长篇批次相关 action type、builder 和 detail helper。`agentRunProjection.ts` 保留通用 registry、恢复执行、Trace 审计和运行 ID 抽取逻辑，并从新模块导入长篇 descriptor。

**Tech Stack:** TypeScript、Vue 3、Vitest。

---

## Files

- Create: `frontend/src/components/chat/longformAgentRunProjection.ts`
  - Export longform action type list.
  - Export descriptor map for longform batch, preflight, prepare, execute, review, and route tools.
  - Own its longform-specific helper functions.
- Modify: `frontend/src/components/chat/agentRunProjection.ts`
  - Import longform action types and descriptors.
  - Remove longform helper functions from the generic file.
- Modify: `frontend/src/components/chat/agentRunProjection.test.ts`
  - Assert longform module exports the expected action types and descriptors.

## Success Criteria

- `agentRunProjection.ts` no longer defines `buildLongform*` helper functions.
- `longformAgentRunProjection.ts` owns all longform-specific label/detail extraction.
- Existing public behavior of `buildAgentRunActionResultView` remains unchanged.
- `getAgentRunIdFromMessage` still extracts run IDs for longform action types.
- Existing chat rendering tests remain green.

## Tasks

### Task 1: Write Failing Module Boundary Tests

- [x] In `agentRunProjection.test.ts`, import:

```ts
import {
  LONGFORM_AGENT_RUN_ACTION_TYPES,
  LONGFORM_AGENT_RUN_ACTION_DESCRIPTORS,
} from './longformAgentRunProjection'
```

- [x] Add a test asserting `LONGFORM_AGENT_RUN_ACTION_TYPES` equals:

```ts
[
  'inspect_longform_chapter_batch',
  'execute_longform_chapter_batch_preflight',
  'prepare_longform_chapter_batch_execution',
  'execute_longform_chapter_batch',
  'review_longform_chapter_batch_execution',
  'route_longform_chapter_batch_after_review',
]
```

- [x] Assert every exported descriptor has a `buildView` function.
- [x] Run:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts
```

Expected: FAIL because `longformAgentRunProjection.ts` does not exist yet.

### Task 2: Extract Longform Module

- [x] Create `longformAgentRunProjection.ts`.
- [x] Move longform builder functions and their helper functions from `agentRunProjection.ts` into the new file.
- [x] Import `ActionResultView` type in the new file.
- [x] In `agentRunProjection.ts`, import `LONGFORM_AGENT_RUN_ACTION_TYPES` and `LONGFORM_AGENT_RUN_ACTION_DESCRIPTORS`.
- [x] Compose:

```ts
export const AGENT_RUN_ACTION_TYPES = [
  'plan_recovery_tools',
  'ui_recovery_execute',
  'inspect_agent_trace_audit',
  ...LONGFORM_AGENT_RUN_ACTION_TYPES,
] as const
```

- [x] Merge longform descriptors into `AGENT_RUN_ACTION_DESCRIPTORS`.
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
- [x] Commit with:

```powershell
git add frontend/src/components/chat/agentRunProjection.ts frontend/src/components/chat/agentRunProjection.test.ts frontend/src/components/chat/longformAgentRunProjection.ts docs/superpowers/plans/long-memory-agent/2026-05-23-phase172-longform-projection-module.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase172-longform-projection-module.md
git commit -m "refactor: split longform chat projections"
git push origin main
```
