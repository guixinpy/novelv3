# Phase72 Recovery Projection Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move recovery/followup projection detail tests out of the aggregate `agentRunProjection.test.ts` file into a dedicated module test.

**Architecture:** `agentRunProjection.test.ts` should only cover aggregate registry/runtime behavior. `recoveryAgentRunProjection.test.ts` should cover recovery/followup descriptors, preview cards, execution cards, Agent discovery detail projection, and recovery execution feedback builders directly through the recovery module API.

**Tech Stack:** Vue frontend, TypeScript, Vitest, Vite build.

---

### Task 1: Recovery Projection Test Boundary

**Files:**
- Create: `frontend/src/components/chat/recoveryAgentRunProjection.test.ts`
- Modify: `frontend/src/components/chat/agentRunProjection.test.ts`
- Create: `docs/superpowers/notes/agent-native-writing/2026-05-25-phase72-recovery-projection-tests.md`

- [ ] **Step 1: Write the failing structure test**

In `agentRunProjection.test.ts`, add a small structure test that reads its own source and asserts it no longer contains recovery/followup detail specs such as:

- `builds fallback views for recovery preview action results`
- `builds recovery execution feedback without leaking plan hash`

Expected initial state: the test fails because these detail specs still live in the aggregate test file.

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
npm run test:unit -- agentRunProjection
```

Expected: fail because `agentRunProjection.test.ts` still contains recovery/followup detail specs.

- [ ] **Step 3: Move recovery/followup detail tests**

Create `recoveryAgentRunProjection.test.ts` and move these behaviors there:

- recovery module descriptors and feedback builder export check.
- recovery preview card.
- recommended followup preview card.
- delegate profile target projection.
- profile policy audit projection.
- recovery execution action card.
- recovery execution feedback without leaking plan hash.
- failed recovery execution feedback with error summary.

Update those tests to call `RECOVERY_AGENT_RUN_ACTION_DESCRIPTORS[type].buildView(...)` or the recovery feedback builder exports directly.

Keep aggregate-only tests in `agentRunProjection.test.ts`:

- registry composition.
- run id extraction.
- unknown action result handling.
- aggregate `isAgentRunActionType` and `getAgentRunActionDescriptor`.

- [ ] **Step 4: Run targeted frontend verification**

Run:

```powershell
npm run test:unit -- agentRunProjection recoveryAgentRunProjection
npm run test:unit -- ChatMessage
npm run build
git diff --check
```

Expected:
- aggregate and recovery tests pass.
- `ChatMessage` passes to cover action card rendering integration.
- `npm run build` succeeds.
- `git diff --check` has no new whitespace issue; the known CRLF warning in `backend/tests/test_writing_agent_runs.py` is unrelated.

- [ ] **Step 5: Write phase report**

Create `docs/superpowers/notes/agent-native-writing/2026-05-25-phase72-recovery-projection-tests.md` with scope, files changed, red/green evidence, verification evidence, and next suggested phase.
