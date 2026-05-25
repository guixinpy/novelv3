# Phase165 Trace Audit Chat Projection Report

## Summary

本阶段把第一个非恢复类 Agent 工具事件 `inspect_agent_trace_audit` 接入前端 descriptor registry。Hermes 聊天消息即使缺少后端 `action_result_view`，也能显示稳定中文 Trace 审计投影，不再暴露 raw `inspect_agent_trace_audit`。

这是从恢复链路走向通用 Agent 工具事件投影的第一步。

## Changes

- `frontend/src/components/chat/agentRunProjection.ts`
  - Registered `inspect_agent_trace_audit`.
  - Added Trace audit fallback label and detail projection.
  - Added nested `data.run.id` run id extraction.
  - Added run status, step count, trace count, failure reason, and recommended action count details.
- `frontend/src/components/chat/agentRunProjection.test.ts`
  - Added descriptor coverage.
  - Added nested run id extraction coverage.
  - Added Trace audit fallback view coverage.
- `frontend/src/components/chat/ChatMessage.test.ts`
  - Added ChatMessage fallback rendering coverage for Trace audit messages.

## TDD Evidence

RED command:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts src/components/chat/ChatMessage.test.ts
```

Expected failures:

- `inspect_agent_trace_audit` was not recognized as an Agent run action.
- Descriptor lookup returned undefined.
- Nested `data.run.id` was not extracted.
- ChatMessage rendered raw `inspect_agent_trace_audit`.

GREEN command:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts src/components/chat/ChatMessage.test.ts
```

Result:

- 2 test files passed.
- 26 tests passed.

## Validation

Targeted frontend regression:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts src/components/chat/ChatMessage.test.ts src/views/HermesView.test.ts
```

Result:

- 3 test files passed.
- 31 tests passed.

Build:

```powershell
cd frontend
npm run build
```

Result: `vue-tsc --noEmit` and `vite build` passed.

Hygiene:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

Result:

- `git diff --check`: passed.
- secret scan: no matches.

## Next Recommendation

下一阶段建议接入第二个非恢复类工具事件，优先选择 `inspect_longform_chapter_batch`。它直接关联长篇稳定写作的任务队列/批量章节推进，是将 Agent 工具投影从 Trace 诊断扩展到长篇生产链路的合适下一步。
