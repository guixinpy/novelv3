# Phase156 Recovery Policy Visibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show recovery preview execution policy and guardrails in the Writing Agent run drawer.

**Architecture:** Keep recovery planning unchanged. `AgentRunDrawer` will derive a compact recovery preview view from the `plan_recovery_tools` step output and render policy status, confirmation requirements, safe-auto-execute flag, guardrail blockers, and recovery tools.

**Tech Stack:** Vue 3, TypeScript, Vitest, existing Writing Agent run detail payload.

---

## Scope

In scope:
- Parse `execution_policy`, `guardrails`, and `tools` from the `plan_recovery_tools` step output.
- Display execution policy as Chinese, user-facing status.
- Display guardrail blockers with code/message/tool name.
- Display recovery tool names.
- Preserve the existing compact drawer layout and step list.

Out of scope:
- Executing recovery from the drawer.
- Adding confirmation buttons.
- Changing backend recovery planning.
- Adding route-level Agent run pages.

## Files

- Modify: `frontend/src/components/writingAgent/AgentRunDrawer.vue`
- Modify: `frontend/src/components/writingAgent/AgentRunDrawer.test.ts`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase156-recovery-policy-visibility.md`

## Task 1: RED Test

- [x] **Step 1: Add failing drawer test for policy and guardrails**

Add `renders recovery execution policy and guardrails` to `AgentRunDrawer.test.ts`.

The run should include a `plan_recovery_tools` step output:

```ts
{
  execution_policy: {
    mode: 'preview',
    status: 'requires_user_input',
    requires_confirmation: true,
    requires_plan_hash: true,
    safe_auto_execute: false,
  },
  guardrails: {
    status: 'blocked',
    blockers: [
      {
        code: 'requires_user_input',
        tool_name: 'prepare_generate_chapter_execution',
        message: '恢复工具需要用户补充输入，不能自动执行。',
      },
    ],
  },
  tools: [{ tool_name: 'prepare_generate_chapter_execution' }],
}
```

Assert the drawer text contains:
- `恢复执行策略`
- `需要用户补充输入`
- `需要确认`
- `需要计划哈希`
- `不允许自动执行`
- `保护策略`
- `恢复工具需要用户补充输入`
- `prepare_generate_chapter_execution`

- [x] **Step 2: Run RED**

Run:

```powershell
Set-Location frontend; npm run test:unit -- src/components/writingAgent/AgentRunDrawer.test.ts
```

Expected: fails because no recovery policy/guardrail section is rendered yet.

## Task 2: Drawer Rendering

- [x] **Step 1: Add computed recovery preview extraction**

Modify `AgentRunDrawer.vue`:
- find the first step whose `tool_name === "plan_recovery_tools"`.
- use its `output` as the recovery preview payload.
- normalize `execution_policy`, `guardrails`, and `tools`.

- [x] **Step 2: Add label helpers**

Add helpers:
- `policyStatusLabel(status)`
- `booleanLabel(value, trueLabel, falseLabel)`
- `guardrailStatusLabel(status)`

Use Chinese labels:
- `ready` -> `可执行`
- `requires_user_input` -> `需要用户补充输入`
- `confirmation_required` -> `等待确认`
- `repeat_failed_recovery` -> `重复失败保护`
- `blocked` -> `已阻止`

- [x] **Step 3: Render policy and guardrails**

Add sections before the step list:
- policy facts in a compact grid.
- guardrail blockers list if blockers exist.
- recovery tools list if tools exist.

- [x] **Step 4: Run GREEN**

Run:

```powershell
Set-Location frontend; npm run test:unit -- src/components/writingAgent/AgentRunDrawer.test.ts
```

Expected: tests pass.

## Task 3: Regression, Report, Commit

- [x] **Step 1: Run targeted frontend regression**

Run:

```powershell
Set-Location frontend; npm run test:unit -- src/components/writingAgent/AgentRunDrawer.test.ts src/views/HermesView.test.ts
```

Expected: selected tests pass.

- [x] **Step 2: Run T1 build/type check**

Run:

```powershell
Set-Location frontend; npm run build
```

Expected: build passes.

- [x] **Step 3: Run hygiene checks**

Run from repo root:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

Expected: diff check passes; secret scan returns no matches.

- [x] **Step 4: Write phase report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-23-phase156-recovery-policy-visibility.md`.

- [x] **Step 5: Commit and push**

Run:

```powershell
git add frontend/src/components/writingAgent/AgentRunDrawer.vue frontend/src/components/writingAgent/AgentRunDrawer.test.ts docs/superpowers/plans/long-memory-agent/2026-05-23-phase156-recovery-policy-visibility.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase156-recovery-policy-visibility.md
git commit -m "feat: show recovery policy in agent run drawer"
git push
```
