# Phase44: Chat Command Contract Feedback

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让聊天侧 Agent run feedback 卡片复用 Phase43 的 `agent_command_contracts` 摘要，用户无需打开运行抽屉也能看到命令控制面健康概况。

**Architecture:** 前端 `agentRunProjection.ts` 已有 `agentDiscoveryDetailItems(...)` 作为 Agent run feedback 的共享摘要入口。本阶段只在该共享入口中追加命令契约轻量 detail item，不扩展 action 类型，不展示完整命令列表。

**Tech Stack:** Vue 3 TypeScript、Vitest。

---

## 参考项目吸收

- hermes-agent：运行反馈应快速显示控制面健康信号，减少用户翻内部 trace 的成本。
- openhuman：聊天反馈只展示 bounded summary，不泄露冗长 provenance 或内部列表。

## 成功标准

1. `buildAgentRunExecutionFeedback(...)` 接收到 `agent_command_contracts` 时，`action_result_view.detail_items` 展示：
   - `命令契约: 已投影`
   - `控制命令: N 个`
   - `契约缺口: N 个`
2. 不展示完整 `commands` 列表或内部 source path。
3. 不影响现有 recovery/followup/action fallback view。

## Task 1: Frontend Feedback Projection

**Files:**
- Modify: `frontend/src/components/chat/agentRunProjection.ts`
- Test: `frontend/src/components/chat/agentRunProjection.test.ts`

- [ ] **Step 1: Write failing test**

Extend `builds recovery execution feedback without leaking plan hash` with:

```ts
agent_command_contracts: {
  source: 'planner_trace.agent_health_projection.command_contracts',
  summary: {
    agent_control_commands: 2,
    gap_count: 0,
  },
},
```

Assert:

```ts
expect(message.action_result_view.detail_items).toContainEqual({ label: '命令契约', value: '已投影' })
expect(message.action_result_view.detail_items).toContainEqual({ label: '控制命令', value: '2 个' })
expect(message.action_result_view.detail_items).toContainEqual({ label: '契约缺口', value: '0 个' })
expect(JSON.stringify(message)).not.toContain('planner_trace.agent_health_projection.command_contracts')
```

- [ ] **Step 2: Verify RED**

Run:

```powershell
cd frontend; .\node_modules\.bin\vitest run src/components/chat/agentRunProjection.test.ts -t "builds recovery execution feedback without leaking plan hash"
```

Expected: FAIL because command contract detail items are absent.

- [ ] **Step 3: Implement minimal projection**

Add `agentCommandContractDetailItems(data)` and append it from `agentDiscoveryDetailItems(data)`.

- [ ] **Step 4: Verify GREEN**

Run:

```powershell
cd frontend; .\node_modules\.bin\vitest run src/components/chat/agentRunProjection.test.ts -t "builds recovery execution feedback without leaking plan hash"
```

Expected: PASS.

## Task 2: Phase Verification and Report

**Files:**
- Create: `docs/superpowers/notes/agent-native-writing/2026-05-25-phase44-chat-command-contract-feedback.md`

- [ ] **Step 1: Run targeted verification**

Run:

```powershell
cd frontend; .\node_modules\.bin\vitest run src/components/chat/agentRunProjection.test.ts
cd frontend; .\node_modules\.bin\vue-tsc --noEmit
cd ..; git diff --check
```

- [ ] **Step 2: Write phase report**

Record RED evidence, GREEN evidence, changed files, and next-phase recommendation.
