# Phase204 Route Upgrade Guarded Apply Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 Phase203 生成的路由升级审批契约接入 Agent run drawer 中的显式 guarded apply 入口，让用户在查看契约摘要后手动应用路由 opt-in，但仍不执行原 pending action。

**Architecture:** `ActionCard` 只负责生成只读审批契约；`AgentRunDrawer` 只在契约 run 满足 `requires_confirmation` 且推荐 `apply_pending_action_route_approval_opt_in` 时显示确认入口；`HermesView` 从当前 run 内部 output 读取 hash/contract 并创建 guarded apply Agent run；`chat.ts` 只追加 UI-safe 反馈消息。

**Tech Stack:** Vue 3, Pinia, Vitest, existing Writing Agent run API, Python backend existing route opt-in tools.

---

## Reference Project Inputs

- `references/agent-projects/openclaw/src/agents/bash-tools.exec-approval-request.ts`：采用 two-phase approval registration，先注册审批请求，再等待决策，避免用户确认与执行状态竞态。Phase204 转译为“先 preview 契约，再 drawer 手动 apply”的两段式流。
- `references/agent-projects/openclaw/src/agents/bash-tools.exec-approval-followup-state.ts`：handoff 中保留运行时敏感上下文，UI 只拿稳定 ID / 摘要。Phase204 保持 approval hash/contract 只在当前 run output 和 API request 中流转，不写入本地聊天消息。
- `references/agent-projects/hermes-agent/tools/registry.py`：工具注册与工具暴露分离。Phase204 不把 apply 按钮放回 `ActionCard`，只在 Agent run drawer 基于 run output 暴露下一步。
- `references/agent-projects/hermes-agent/tools/approval.py` / `acp_adapter/permissions.py`：审批选项映射为受限决策，不让普通消息绕过控制流。Phase204 的 apply action 必须显式 `confirm_apply: true`，不能经 `resolveAction(confirm)`。
- `references/agent-projects/openhuman/src/openhuman/tools/traits.rs`：工具有 permission level / scope / unified result 概念。Phase204 将 route apply 视作 write-scope 工具，UI 只展示安全摘要，执行结果走现有 `ActionResultView` 投影。

## Files

- Modify: `frontend/src/components/writingAgent/AgentRunDrawer.vue`
  - 增加 route opt-in contract preview 的摘要区。
  - 在 eligible contract run 中显示“确认应用路由升级”按钮。
  - emit `applyRouteUpgrade`，payload 只包含 `sourceRunId/pendingActionId/approvalContractHash/approvalContract`，不显示在 DOM。
- Modify: `frontend/src/components/writingAgent/AgentRunDrawer.test.ts`
  - RED/GREEN 覆盖 eligible、ineligible、no leak 三类行为。
- Modify: `frontend/src/views/HermesView.vue`
  - 处理 drawer 的 `apply-route-upgrade` 事件。
  - 创建 `apply_pending_action_route_approval_opt_in` Agent run。
  - 不调用 `resolveAction`，不确认/取消原 pending action。
- Modify: `frontend/src/views/HermesView.test.ts`
  - 覆盖 drawer 事件到 `api.createAgentRun()` 的工具请求。
  - 确认可见消息不泄露 hash/contract。
- Modify: `frontend/src/stores/chat.ts`
  - 增加 `appendRouteUpgradeApplyFeedback(run)`，生成 UI-safe apply 反馈消息。
- Modify: `frontend/src/stores/chat.workspace.test.ts`
  - 覆盖 apply 反馈消息不泄露 hash/contract/internal params。
- Modify: `docs/superpowers/notes/long-memory-agent/2026-05-24-phase204-route-upgrade-guarded-apply.md`
  - 阶段报告：RED/GREEN、验证证据、参考项目转译、下一阶段。

## Tasks

### Task 1: Drawer Contract Apply UI

- [ ] **Step 1: Write failing drawer tests**

Add tests in `frontend/src/components/writingAgent/AgentRunDrawer.test.ts`:

```ts
it('renders route upgrade guarded apply only for eligible contract preview runs without leaking contract internals', async () => {
  const wrapper = mount(AgentRunDrawer, {
    attachTo: document.body,
    props: {
      open: true,
      loading: false,
      error: '',
      run: {
        id: 'run-contract',
        project_id: 'project-1',
        goal: '生成待确认操作的路由升级审批契约',
        status: 'success',
        entrypoint: 'pending_action_safety_action',
        input: {},
        output: null,
        error: null,
        steps: [
          {
            id: 'step-contract',
            run_id: 'run-contract',
            project_id: 'project-1',
            step_index: 1,
            tool_name: 'preview_pending_action_route_approval_opt_in_apply_contract',
            status: 'success',
            input: {},
            output: {
              status: 'requires_confirmation',
              required_confirmation: true,
              pending_action_id: 'action-1',
              approval_contract_hash: 'approval:secret',
              approval_contract: { approval: { approval_contract_hash: 'approval:secret' } },
              recommended_next_tools: ['apply_pending_action_route_approval_opt_in'],
            },
          },
        ],
      },
    },
  })

  const text = document.body.textContent || ''
  expect(text).toContain('路由升级审批')
  expect(text).toContain('等待确认')
  expect(text).toContain('需要确认')
  expect(text).not.toContain('approval:secret')
  expect(text).not.toContain('approval_contract')

  const button = document.body.querySelector('[data-testid="apply-route-upgrade"]') as HTMLButtonElement
  expect(button).not.toBeNull()
  await button.click()

  expect(wrapper.emitted('applyRouteUpgrade')).toEqual([[
    {
      sourceRunId: 'run-contract',
      pendingActionId: 'action-1',
      approvalContractHash: 'approval:secret',
      approvalContract: { approval: { approval_contract_hash: 'approval:secret' } },
    },
  ]])
})

it('does not render route upgrade apply when contract preview is not confirmable', () => {
  mount(AgentRunDrawer, {
    attachTo: document.body,
    props: {
      open: true,
      loading: false,
      error: '',
      run: {
        id: 'run-contract',
        project_id: 'project-1',
        goal: '无需升级',
        status: 'success',
        entrypoint: 'pending_action_safety_action',
        input: {},
        output: null,
        error: null,
        steps: [
          {
            id: 'step-contract',
            run_id: 'run-contract',
            project_id: 'project-1',
            step_index: 1,
            tool_name: 'preview_pending_action_route_approval_opt_in_apply_contract',
            status: 'success',
            input: {},
            output: {
              status: 'not_required',
              required_confirmation: false,
              pending_action_id: 'action-1',
              recommended_next_tools: [],
            },
          },
        ],
      },
    },
  })

  expect(document.body.querySelector('[data-testid="apply-route-upgrade"]')).toBeNull()
})
```

- [ ] **Step 2: Run RED**

Run:

```powershell
npm --prefix frontend run test:unit -- AgentRunDrawer
```

Expected: FAIL because `applyRouteUpgrade` emit and button do not exist.

- [ ] **Step 3: Implement minimal drawer support**

In `AgentRunDrawer.vue`:

- add `applyRouteUpgrade` emit;
- compute latest route contract preview output;
- require status `requires_confirmation`, `required_confirmation === true`, string `approval_contract_hash`, object `approval_contract`, and recommended next tool/call containing `apply_pending_action_route_approval_opt_in`;
- render a compact summary using Chinese labels only;
- button emits payload with raw hash/contract but does not render them.

- [ ] **Step 4: Run GREEN**

Run:

```powershell
npm --prefix frontend run test:unit -- AgentRunDrawer
```

Expected: PASS.

### Task 2: Hermes Apply Run Integration

- [ ] **Step 1: Write failing HermesView test**

Add a test in `frontend/src/views/HermesView.test.ts` where the stub drawer emits `applyRouteUpgrade` and verify:

- `api.createAgentRun()` is called with tool `apply_pending_action_route_approval_opt_in`;
- params include `pending_action_id`, `confirm_apply: true`, `approval_contract_hash`, `approval_contract`;
- `api.resolveAction()` is not called;
- visible feedback does not contain `approval:secret` or `approval_contract`.

- [ ] **Step 2: Run RED**

Run:

```powershell
npm --prefix frontend run test:unit -- HermesView
```

Expected: FAIL because `applyRouteUpgrade` is not handled.

- [ ] **Step 3: Implement minimal HermesView handler**

In `HermesView.vue`:

- define `RouteUpgradeApplyPayload`;
- add `applyRouteUpgradeFromRun(payload)`;
- call `api.createAgentRun(pid.value, { entrypoint: 'pending_action_route_upgrade_apply', tools: [...] })`;
- set active drawer to returned run;
- call `chat.appendRouteUpgradeApplyFeedback(run)`;
- wire `@apply-route-upgrade`.

- [ ] **Step 4: Run GREEN**

Run:

```powershell
npm --prefix frontend run test:unit -- HermesView
```

Expected: PASS.

### Task 3: UI-Safe Apply Feedback

- [ ] **Step 1: Write failing store test**

Add a test in `frontend/src/stores/chat.workspace.test.ts` for `appendRouteUpgradeApplyFeedback(run)`:

- action type is `apply_pending_action_route_approval_opt_in`;
- data only contains `agent_run_id`, `status`, optional `write_performed`/`reason`;
- JSON does not contain `approval:secret`, `approval_contract`, or raw params.

- [ ] **Step 2: Run RED**

Run:

```powershell
npm --prefix frontend run test:unit -- chat.workspace
```

Expected: FAIL because helper does not exist.

- [ ] **Step 3: Implement feedback helper**

In `chat.ts`, add `appendRouteUpgradeApplyFeedback(run)` using existing `buildAgentRunActionResultView()` projection.

- [ ] **Step 4: Run GREEN**

Run:

```powershell
npm --prefix frontend run test:unit -- chat.workspace
```

Expected: PASS.

### Task 4: Review and Validation

- [ ] **Step 1: Request focused review**

Ask a review subagent to inspect:

- no ActionCard apply execution;
- no `resolveAction(confirm)` path;
- no hash/contract leak in user-visible message or drawer DOM;
- guarded apply only mutates route opt-in, not original pending action.

- [ ] **Step 2: Run T2 validation**

Run:

```powershell
npm --prefix frontend run test:unit -- AgentRunDrawer HermesView chat.workspace agentRunProjection
npm --prefix frontend run build
python -m compileall backend/app/services/writing_agent backend/app/api/dialogs.py
git diff --check
rg -n "<real DeepSeek key prefix>" .
```

Expected:

- Vitest targeted files pass.
- Frontend build passes.
- Compileall passes.
- Diff check passes.
- Secret scan has no matches.

- [ ] **Step 3: Update phase report and commit**

Update report with RED/GREEN/T2 evidence, review findings, and next phase recommendation.

Commit message:

```text
feat: apply route upgrade from agent run drawer
```
