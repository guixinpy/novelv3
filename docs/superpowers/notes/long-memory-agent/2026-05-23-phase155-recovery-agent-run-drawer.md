# Phase155 Recovery Agent Run Drawer Report

## Summary

Recovery-preview chat messages now expose a user-facing "查看运行" action. Clicking it loads the Writing Agent run detail through the existing `/agent-runs/{run_id}` API and opens a lightweight drawer with run metadata and tool steps.

## Changes

- Added `WritingAgentRunDetail` and `WritingAgentStep` frontend API types.
- Added `api.getAgentRun(projectId, runId)`.
- Added a `ChatMessage` recovery-preview action button that resolves the run id from message `meta.agent_run_id` or `action_result.data.agent_run_id`.
- Forwarded `openAgentRun` through `ChatMessageList`.
- Added `AgentRunDrawer.vue` for compact run inspection.
- Wired `HermesView` to fetch and display the drawer.

## Validation

RED chat component tests:

```powershell
Set-Location frontend; npm run test:unit -- src/components/chat/ChatMessage.test.ts src/components/chat/ChatMessageList.test.ts
```

Result: failed because `[data-testid="open-agent-run"]` did not exist.

GREEN chat component tests:

```powershell
Set-Location frontend; npm run test:unit -- src/components/chat/ChatMessage.test.ts src/components/chat/ChatMessageList.test.ts
```

Result: `2 passed`, `15 passed`.

RED drawer/Hermes tests:

```powershell
Set-Location frontend; npm run test:unit -- src/components/writingAgent/AgentRunDrawer.test.ts src/views/HermesView.test.ts
```

Result: failed because `AgentRunDrawer.vue` did not exist and Hermes did not call `api.getAgentRun`.

GREEN drawer/Hermes tests:

```powershell
Set-Location frontend; npm run test:unit -- src/components/writingAgent/AgentRunDrawer.test.ts src/views/HermesView.test.ts
```

Result: `2 passed`, `5 passed`.

Targeted frontend regression:

```powershell
Set-Location frontend; npm run test:unit -- src/components/chat/ChatMessage.test.ts src/components/chat/ChatMessageList.test.ts src/components/writingAgent/AgentRunDrawer.test.ts src/views/HermesView.test.ts
```

Result: `4 passed`, `20 passed`.

Build/type check:

```powershell
Set-Location frontend; npm run build
```

Result: `vue-tsc --noEmit && vite build` passed.

Hygiene:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

Result: diff check passed; secret scan found no matches.

## Long-Goal Implication

Agent orchestration artifacts are now inspectable from the primary conversation surface. This reduces the gap between "Agent planned something" and "user can inspect what the Agent actually did", which is necessary for long-running writing automation and recovery.

## Next Recommendation

Continue converting recovery and follow-up flows into first-class inspectable Agent operations. A high-value next phase is to add frontend visibility for recovery preview execution policy, including whether the suggested recovery is executable, blocked by guardrails, or waiting for user confirmation.
