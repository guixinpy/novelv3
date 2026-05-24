# Phase203 Pending Action Safety Action Report

## Scope

把 Phase202 的 pending action 安全提示推进为用户可触发的安全准备动作：

- 在 pending action 卡片上提供“生成审批契约”按钮；
- 点击只创建只读 Agent run，执行 `preview_pending_action_route_approval_opt_in_apply_contract`；
- 不执行 `apply_pending_action_route_approval_opt_in`；
- 不确认、不取消、不修改原 pending action；
- 不在 pending card 或本地反馈消息中展示 approval hash、完整 approval contract、route diff 或内部工具参数。

## Plan

见 `docs/superpowers/plans/long-memory-agent/2026-05-24-phase203-pending-action-safety-action.md`。

## RED

- Backend:
  - `pytest backend/tests/test_dialogs.py -k "safety_view" -q`
  - 结果：`7 failed, 86 deselected`
  - 预期失败：
    - `recommendation["action"]` 不存在；
    - `pending_action_safety_view()` 不接受 `pending_action_id` 参数。
- Frontend components:
  - 初次 `npm --prefix frontend run test:unit -- ActionCard ChatMessage ChatMessageList`
  - 结果：测试文件语法错误，原因是新增测试用了 `await` 但用例未声明 `async`。这是测试自身错误，已修正后重跑。
  - 修正后 RED：
    - `3 failed, 25 passed`
    - 预期失败：`pending-action-safety-prepare` 按钮不存在，事件未转发。
- Frontend store:
  - `npm --prefix frontend run test:unit -- chat.workspace`
  - 结果：`1 failed, 25 passed`
  - 预期失败：`store.preparePendingActionSafetyAction is not a function`。

## Implementation

- Backend:
  - `pending_action_safety_view()` 增加 `pending_action_id` 可选参数。
  - 在可升级 route 的推荐项上增加抽象 action：
    - `kind=prepare_route_upgrade_contract`
    - `label=生成审批契约`
    - `pending_action_id`
    - `auto_execute=false`
    - `guarded_apply=false`
  - `_pending_action_out()` 与 `DialogMessageService._pending_action_payload()` 均传入 `pending.id`，保持即时响应与历史消息一致。
- Frontend components:
  - `PendingActionSafetyRecommendation` 增加可选 `action`。
  - `ActionCard` 只在 action 满足以下条件时显示按钮：
    - `kind === prepare_route_upgrade_contract`
    - action 的 `pending_action_id` 等于当前 pending action id
    - `auto_execute !== true`
    - `guarded_apply !== true`
  - 按钮只 emit 脱敏后的抽象 action，不 emit 内部工具名。
  - `ChatMessage` / `ChatMessageList` 转发 `safetyAction` 事件。
- Store / Hermes:
  - `chat.preparePendingActionSafetyAction()` 创建只读 Agent run：
    - `tool_name=preview_pending_action_route_approval_opt_in_apply_contract`
    - `entrypoint=pending_action_safety_action`
  - 本地追加一条脱敏 system message，只保留 `agent_run_id/status/required_confirmation`。
  - 原 `pendingAction` 不清空。
  - `HermesView` 接入 `@safety-action`，并打开对应 Agent run 详情。
- Review feedback fixes:
  - 本地反馈消息 `action_result.type` / `meta.agent_action_type` 改为 UI-safe `prepare_route_upgrade_contract`，内部 preview 工具名只保留在 `api.createAgentRun()` 的实际工具请求中。
  - `agentRunProjection` 注册 `prepare_route_upgrade_contract`，保持“查看运行”能力。
  - 补充 `pending_action_id` 不匹配、`auto_execute=true`、`guarded_apply=true` 三类负向 store 测试。
  - 补充 `HermesView` safety-action 集成测试，证明该事件不调用 `resolveAction`，不走 pending action 决策路径。

## Validation

- GREEN:
  - `pytest backend/tests/test_dialogs.py -k "safety_view" -q`
    - `7 passed, 86 deselected`
  - `npm --prefix frontend run test:unit -- ActionCard ChatMessage ChatMessageList`
    - `3 passed` test files, `28 passed`
  - `npm --prefix frontend run test:unit -- chat.workspace`
    - 初次 `26 passed`
  - `npm --prefix frontend run test:unit -- HermesView`
    - `5 passed`
  - Review feedback tests:
    - `npm --prefix frontend run test:unit -- chat.workspace HermesView agentRunProjection`
    - `3 passed` test files, `69 passed`
- T2:
  - `pytest backend/tests/test_dialogs.py -k "safety_view or pending_action" -q`
    - `16 passed, 77 deselected`
  - `npm --prefix frontend run test:unit -- ActionCard ChatMessage ChatMessageList chat.workspace HermesView agentRunProjection`
    - 初次 `6 passed` test files, `93 passed`
    - 处理 review feedback 后重跑：`6 passed` test files, `97 passed`
  - `npm --prefix frontend run build`
    - 初次失败：新增测试使用 `Array.prototype.at()`，当前 TS lib 不支持。
    - 修正为索引访问后通过；处理 review feedback 后再次通过，`vue-tsc --noEmit && vite build` exit 0。
  - `python -m compileall backend/app/services/actions backend/app/services/dialog backend/app/api/dialogs.py`
    - exit 0
  - `git diff --check`
    - exit 0
  - 真实 DeepSeek key 前缀扫描
    - 初次命中本计划文档中的真实 key 前缀示例命令，已改为占位。
    - 重扫 exit 1，无命中。

## Review

- Review subagent `019e57ee-2763-74d1-90f6-9681d26638e1`
  - Critical: 无。
  - Important: 无。
  - Minor:
    - 本地反馈消息对象仍包含内部 preview 工具名。已改为 UI-safe `prepare_route_upgrade_contract`。
    - 缺少 unsafe action 负向测试。已补 `pending_action_id` mismatch、`auto_execute=true`、`guarded_apply=true`。
    - HermesView 缺少 safety-action 事件覆盖。已补集成测试并确认不调用 `resolveAction`。
  - 结论：处理反馈后，本阶段仍只创建 read-only preview Agent run；不会执行 guarded apply，不会确认/取消/修改原 pending action。

## Novel Progress

本阶段不推进小说正文生成。原因：Phase203 仍属于对话入口 Agent 化的安全交互链路，把 legacy pending action 迁往 approval-chain 前，需要先让用户可控地生成审批契约。

## Next

- 下一阶段可把“生成审批契约”后的下一步从 Agent run drawer 中继续收敛为显式用户确认流程：用户查看契约摘要后，再通过 guarded apply 写入 route opt-in。仍不得让 ActionCard 直接执行 apply。
