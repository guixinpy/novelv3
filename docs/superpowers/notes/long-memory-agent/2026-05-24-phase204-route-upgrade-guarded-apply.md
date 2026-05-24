# Phase204 Route Upgrade Guarded Apply Report

## Scope

把 Phase203 的“生成审批契约”推进到下一步：在 Agent run drawer 中提供显式 guarded apply 入口。该入口只应用 `PendingAction.params.agent_route.use_agent_approval_chain`，不执行原 pending action，也不走 legacy `resolveAction(confirm)`。

## Plan

见 `docs/superpowers/plans/long-memory-agent/2026-05-24-phase204-route-upgrade-guarded-apply.md`。

## Reference Project Translation

- OpenClaw two-phase approval：采用 preview contract -> drawer confirm apply 的两阶段链路，避免确认与执行竞态。
- OpenClaw followup handoff：敏感 contract 只在运行态 payload 流转，不写入可见聊天消息。
- Hermes tool registry/toolsets：工具注册与 UI 暴露分离，ActionCard 不直接暴露 write 工具。
- Hermes/OpenHuman approval/tool scope：apply 被视作 write-scope guarded tool，只能通过明确确认入口创建 Agent run。

## RED

- Drawer:
  - `npm --prefix frontend run test:unit -- AgentRunDrawer`
  - 结果：`1 failed, 6 passed`
  - 预期失败：eligible contract preview run 不显示“等待确认”和 apply 按钮。
- Hermes:
  - `npm --prefix frontend run test:unit -- HermesView`
  - 结果：`2 failed, 5 passed`
  - 预期失败：`applyRouteUpgrade` 未处理，`api.createAgentRun()` 没有被调用。
  - 附带测试污染：新增 apply mock 影响 recovery 执行测试，后续通过更精确的 mock 顺序与事件处理修正。
- Store:
  - `npm --prefix frontend run test:unit -- chat.workspace`
  - 结果：`1 failed, 29 passed`
  - 预期失败：`store.appendRouteUpgradeApplyFeedback is not a function`。

## Implementation

- `AgentRunDrawer`
  - 增加 `pendingActionId` prop。
  - 从 run steps 中识别 `preview_pending_action_route_approval_opt_in_apply_contract` 的契约输出。
  - 只在以下条件全部满足时显示“确认应用路由升级”：
    - run entrypoint 为 `pending_action_safety_action`；
    - run status 为 `success`；
    - 契约 status 为 `requires_confirmation`；
    - `required_confirmation === true`；
    - 有 `approval_contract_hash` 和 `approval_contract`；
    - 推荐下一步包含 `apply_pending_action_route_approval_opt_in`；
    - 契约 pending action id 与当前 `pendingActionId` 一致。
  - drawer 只显示中文摘要，不展示 approval hash、完整 contract 或 `confirm_apply`。
- `HermesView`
  - 增加 `applyRouteUpgradeFromRun()`。
  - 只接受来源 run 等于当前 active run、pending action id 等于当前 `chat.pendingAction.id` 的事件。
  - 创建新的 Agent run：
    - `entrypoint=pending_action_route_upgrade_apply`
    - tool 为 `apply_pending_action_route_approval_opt_in`
    - params 包含 `pending_action_id`、`confirm_apply=true`、`approval_contract_hash`、`approval_contract`
  - 不调用 `chat.resolveAction()`，不确认、不取消、不执行原 pending action。
- `chat.ts`
  - 增加 `appendRouteUpgradeApplyFeedback(run)`。
  - 本地 system message 只保留 `agent_run_id/status/write_performed/reason`，并走 `buildAgentRunActionResultView()` 生成 UI-safe 投影。

## Validation

- GREEN:
  - `npm --prefix frontend run test:unit -- AgentRunDrawer`
    - `8 passed`
  - `npm --prefix frontend run test:unit -- HermesView`
    - `8 passed`
  - `npm --prefix frontend run test:unit -- chat.workspace`
    - `30 passed`
- T2:
  - `npm --prefix frontend run test:unit -- AgentRunDrawer HermesView chat.workspace agentRunProjection`
    - `4 passed` test files, `80 passed`
  - `npm --prefix frontend run build`
    - `vue-tsc --noEmit && vite build` exit 0
  - `python -m compileall backend/app/services/writing_agent backend/app/api/dialogs.py`
    - exit 0
  - `git diff --check`
    - exit 0
  - 真实 DeepSeek key 前缀扫描
    - exit 1，无命中

## Review

- Review subagent `019e57fb-19e3-7262-92d4-fa432a2f0093`
  - Critical:
    - 指出 ActionCard 仍可让用户确认原 pending action。该项不采纳为 Phase204 bug：本阶段禁止的是 route upgrade apply 链路绕过 Agent run drawer 触发 `resolveAction(confirm)`，不是移除原 pending action 的正常人工决策入口。保留原入口有必要，否则用户无法在 opt-in 后继续执行当前 pending action。
  - Important:
    - `HermesView` 未校验 payload source run 与当前 active run 一致。已修。
    - `HermesView` 未校验 payload pending action 与当前 pending action 一致。已修。
    - `AgentRunDrawer` 可从任意 run 展示 apply。已修为只允许 `pending_action_safety_action` 的成功 run，且要求 pending action id 匹配。
  - Minor:
    - HermesView 测试使用 stub drawer，组合 DOM 回归覆盖不足。本阶段已有真实 `AgentRunDrawer` DOM 泄露测试；暂不增加更重的集成测试，避免超出本阶段变更面。

## Novel Progress

本阶段不推进正文生成。原因：当前阶段属于 Agent 工具化安全控制面，把 legacy pending action 迁往可审批的 Agent 工具链，直接影响后续长篇自动化执行安全。

## Next

- 下一阶段可把 route upgrade apply 的完成结果进一步接回 pending action 卡片：在 opt-in 成功后刷新历史或轻量刷新 pending action，使用户能看到“此待确认动作已启用 Agent 审批链”。仍保持原 pending action 的执行由用户显式确认触发。
- 持续学习参考项目时，下一步应转向统一工具权限/可见性模型：把 OpenHuman 的 `PermissionLevel/ToolScope` 和 Hermes toolset exposure 思路转译到 novelv3 的 Writing Agent tool descriptors。
