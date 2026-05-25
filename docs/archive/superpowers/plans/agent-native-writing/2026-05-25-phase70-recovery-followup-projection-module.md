# Phase70 Recovery Followup Projection Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move recovery/followup chat projection descriptors and execution feedback builders out of the aggregate `agentRunProjection.ts` file into a dedicated module.

**Architecture:** `agentRunProjection.ts` remains the public aggregation surface for action-type detection and generic view building. The new `recoveryAgentRunProjection.ts` owns recovery/followup preview cards, execution cards, execution feedback messages, Agent discovery detail projection, and related status labels. The aggregate module imports/spreads descriptors and re-exports the existing feedback builder API to avoid changing consumers.

**Tech Stack:** Vue frontend, TypeScript, Vitest, Vite build.

---

### Task 1: Recovery/Followup Projection Boundary

**Files:**
- Create: `frontend/src/components/chat/recoveryAgentRunProjection.ts`
- Modify: `frontend/src/components/chat/agentRunProjection.ts`
- Modify: `frontend/src/components/chat/agentRunProjection.test.ts`
- Create: `docs/superpowers/notes/agent-native-writing/2026-05-25-phase70-recovery-followup-projection-module.md`

- [ ] **Step 1: Write the failing test**

Add imports for:

```ts
RECOVERY_AGENT_RUN_ACTION_DESCRIPTORS
RECOVERY_AGENT_RUN_ACTION_TYPES
buildAgentRunExecutionFeedback
buildRecommendedFollowupExecutionFeedback
```

from `./recoveryAgentRunProjection`, then add one module-boundary test that expects the action types to be:

```ts
[
  'plan_recovery_tools',
  'plan_recommended_followups',
  'ui_recovery_execute',
  'ui_recommended_followup_execute',
]
```

Each descriptor must have matching `type` and a `buildView` function. The existing execution feedback tests must continue to use the aggregate exports from `agentRunProjection.ts`.

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
npm run test:unit -- agentRunProjection
```

Expected: fail because `./recoveryAgentRunProjection` does not exist.

- [ ] **Step 3: Write minimal implementation**

Create `recoveryAgentRunProjection.ts` and move the existing recovery/followup code from `agentRunProjection.ts`:

- recovery/followup action types and descriptors.
- `buildAgentRunExecutionFeedback`.
- `buildRecommendedFollowupExecutionFeedback`.
- recovery/followup card builders.
- Agent discovery detail builders currently used only by recovery/followup projection.
- local value helpers needed by the moved code.

Then update `agentRunProjection.ts` to:

- import and spread `RECOVERY_AGENT_RUN_ACTION_TYPES`.
- import and spread `RECOVERY_AGENT_RUN_ACTION_DESCRIPTORS`.
- re-export `buildAgentRunExecutionFeedback`, `buildRecommendedFollowupExecutionFeedback`, and `AgentRunFeedbackMessage` from `recoveryAgentRunProjection.ts`.
- keep `getAgentRunIdFromMessage`, `isAgentRunActionType`, `getAgentRunActionDescriptor`, and `buildAgentRunActionResultView` as aggregate APIs.

- [ ] **Step 4: Run targeted frontend verification**

Run:

```powershell
npm run test:unit -- agentRunProjection
npm run test:unit -- ChatMessage
npm run build
git diff --check
```

Expected:
- `agentRunProjection` passes with the new module-boundary test.
- `ChatMessage` passes to cover action card rendering integration.
- `npm run build` succeeds.
- `git diff --check` has no new whitespace issue; the known CRLF warning in `backend/tests/test_writing_agent_runs.py` is unrelated.

- [ ] **Step 5: Write phase report**

Create `docs/superpowers/notes/agent-native-writing/2026-05-25-phase70-recovery-followup-projection-module.md` with scope, files changed, red/green evidence, verification evidence, and next suggested phase.
