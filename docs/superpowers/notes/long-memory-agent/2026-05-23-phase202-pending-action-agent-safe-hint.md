# Phase202 Pending Action Agent Safe Hint Report

## Scope

把 Phase201 的 route opt-in contract 推荐链，以普通用户可理解、脱敏的方式投影到 pending action 卡片：

- 用户可看到“可先生成路由升级审批契约”；
- 不显示 approval hash、完整 approval contract、route diff 或内部工具参数；
- 不提供绕过 guarded apply 的直接按钮。

## Plan

见 `docs/superpowers/plans/long-memory-agent/2026-05-23-phase202-pending-action-agent-safe-hint.md`。

## RED

- `pytest backend/tests/test_dialogs.py -k "safety_view or get_messages_includes_current_pending_action" -q`
  - 结果：`1 failed, 1 passed, 85 deselected`
  - 预期失败：`PendingActionOut` 尚未输出 `safety_view`。
- `npm --prefix frontend run test:unit -- ActionCard`
  - 结果：`1 failed, 1 passed`
  - 预期失败：`ActionCard` 尚未渲染 `safety_view`。
- 额外发现：
  - 初版测试要求 `str(safety_view)` 不含 `approval_contract`，但推荐 `kind` 使用了 `route_approval_contract_preview`，这会把内部英文契约语义泄露到普通 UI payload。
  - 已将安全推荐 kind 调整为 `route_upgrade_preview`，中文标题仍保留“审批契约”。

## Implementation

- `PendingActionOut` 新增 `safety_view`。
- `pending_action_projection.py` 新增 `pending_action_safety_view(action_type, params)`：
  - 仅当 pending action 带 legacy `agent_route`、尚未 opt-in 且未被 top-level override 禁止时输出；
  - 输出只包含 `kind/title/message/severity/auto_execute/guarded_apply`；
  - 不计算、不返回、不透传 approval hash、approval contract、route diff、params diff、内部工具名或工具参数。
  - 补充负向 gating 测试，覆盖无 `agent_route`、top-level 显式禁用、route 已 opt-in、缺少工具名、空 action type。
- `dialogs.py`
  - 新增 `_pending_action_out(pending)` 统一即时 `ChatOut.pending_action` 构建。
  - 3 处即时 pending action 响应改为复用该 builder。
- `DialogMessageService._pending_action_payload`
  - 历史消息 pending action 投影也补 `safety_view`，与即时响应保持一致。
- `types.ts` / `ActionCard.vue`
  - 增加 `PendingActionSafetyView` 类型。
  - 在确认按钮前展示安全建议标题和消息。
  - 前端只消费 `title/message/severity`，忽略所有未知字段。

## Validation

- GREEN:
  - `pytest backend/tests/test_dialogs.py -k "safety_view" -q`
    - `6 passed, 86 deselected`
  - `pytest backend/tests/test_dialogs.py -k "safety_view or get_messages_includes_current_pending_action" -q`
    - `2 passed, 85 deselected`
  - `npm --prefix frontend run test:unit -- ActionCard`
    - `2 passed`
- T2:
  - `pytest backend/tests/test_dialogs.py -k "pending_action or safety_view or action_result_view" -q`
    - `17 passed, 75 deselected`
  - `npm --prefix frontend run test:unit -- ActionCard ChatMessage agentRunProjection`
    - `4 passed` test files, `60 passed`
  - `npm --prefix frontend run build`
    - `vue-tsc --noEmit && vite build` exit 0
  - `python -m compileall backend/app/services/actions backend/app/services/dialog backend/app/api/dialogs.py`
    - exit 0
  - `git diff --check`
    - exit 0
  - 真实 DeepSeek key 前缀扫描
    - exit 1，无命中

## Review

- Review subagent `019e54c1-e389-7982-abb2-aa5e589a0122`
  - Critical: 无。
  - Important: 无。
  - Minor: 建议补充 `pending_action_safety_view` 负向 gating 测试，避免非升级路线误展示提示。
  - 处理：已补参数化负向测试，并通过 `pytest backend/tests/test_dialogs.py -k "safety_view" -q`。

## Next

- 下一阶段可继续把 pending action 的安全建议从“只读提示”推进到“显式生成审批契约”的用户可控流程，但必须复用 Phase201 guarded apply，不在 ActionCard 里直接执行内部工具。
