# Phase200 Apply Route Opt-In Approval Report

## Summary

新增 guarded mutation 工具 `apply_pending_action_route_approval_opt_in`，用于把现有 `PendingAction.params.agent_route` 切换到 Agent approval-chain opt-in。

核心行为：

- 必须提供 `confirm_apply=True`、`approval_contract_hash`、`approval_contract`。
- 写入前重新计算 Phase198 apply preview 和 Phase199 approval contract。
- 只有 caller hash、caller contract 内嵌 hash、caller contract snapshot 与当前 DB 重算结果全部匹配时才写入。
- 只替换 `PendingAction.params` 为重算得到的 `params_after`，不执行 pending action，不修改 dialog 状态。
- 外部项目或缺失 pending action 返回通用 `pending_action_not_found`，不泄露 params。
- 写入使用整体 JSON 对象赋值，并在 reviewer 反馈后改为绑定 `id/status/resolved_at/current params` 的条件更新。

## Files Changed

- `backend/app/services/writing_agent/slash_command_route.py`
  - Added `PENDING_ACTION_ROUTE_OPT_IN_APPLY_VERSION`.
  - Added apply success/blocked output helpers.
  - Added route opt-in apply contract verification helper.
- `backend/app/services/writing_agent/agent_core_tool_adapters.py`
  - Added adapter `apply_pending_action_route_approval_opt_in`.
  - Added scoped lookup, confirmation validation, recompute-before-write, conditional JSON update.
- `backend/app/services/writing_agent/agent_core_tool_descriptors.py`
  - Added guarded apply descriptor.
- `backend/tests/test_writing_agent_tool_executor.py`
  - Added happy path, missing confirmation/hash/contract, mismatch, stale status/resolved_at/route, foreign ownership, no-diff, metadata, tool contract tests.
- `backend/tests/test_writing_agent_tool_registry.py`
  - Added descriptor order/schema test.
- `backend/tests/test_writing_agent_write_gate_coverage.py`
  - Added direct confirmation guard projection test.

## Review

Explorer `019e5474-f86f-7e32-a189-5aeb6dacc8b1` provided the Phase200 design review:

- Use approved execution pattern with write adapter and confirmation fields.
- Assign a new JSON object to `PendingAction.params`, not nested in-place mutation.
- Recompute preview and contract from current DB state before trusting caller input.
- Avoid foreign params leakage.

Reviewer `019e5481-c4ed-7e83-9b3c-ca0c4e2485c3` found one Important issue:

- Initial implementation recomputed and then directly assigned `pending.params`, leaving a stale Session/concurrent update window.
- Fixed by using `.populate_existing()` for the initial pending lookup and a conditional `update()` bound to `id`, `status`, `resolved_at`, and `params == params_before`.
- Added regression coverage for missing hash/contract, stale `resolved_at`, and route snapshot drift after contract generation.

## Validation

RED:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "apply_route_opt_in_approval or route_opt_in_apply" -q
# 8 failed, 13 passed, 124 deselected
# failure reasons: new apply tool unhandled; adapter metadata missing

pytest backend/tests/test_writing_agent_tool_registry.py -k "apply_route_opt_in_approval or route_opt_in_apply" -q
# 1 failed, 2 passed, 54 deselected
# failure reason: descriptor missing

pytest backend/tests/test_writing_agent_write_gate_coverage.py -k "apply_route_opt_in" -q
# 1 failed, 5 deselected
# failure reason: write-gate projection missing new descriptor
```

GREEN / T1:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "apply_route_opt_in_approval or route_opt_in_apply" -q
# 24 passed, 124 deselected

pytest backend/tests/test_writing_agent_tool_registry.py -k "apply_route_opt_in_approval or route_opt_in_apply" -q
# 3 passed, 54 deselected

pytest backend/tests/test_writing_agent_write_gate_coverage.py -k "apply_route_opt_in" -q
# 1 passed, 5 deselected
```

T2:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "apply_route_opt_in_approval or route_opt_in_apply_contract or route_opt_in_apply or pending_action_route_opt_in_plan or route_approval_opt_in_plan or static_adapter_names or unhandled_internal or inspect_agent_tool_contracts or agent_core_tool_adapters" -q
# 33 passed, 115 deselected

pytest backend/tests/test_writing_agent_tool_registry.py -k "apply_route_opt_in_approval or route_opt_in_apply_contract or route_opt_in_apply_preview or route_approval_opt_in_plan or agent_core_tool_descriptors" -q
# 5 passed, 52 deselected

pytest backend/tests/test_writing_agent_write_gate_coverage.py -q
# 6 passed

python -m compileall backend/app/services/writing_agent
# exit 0
```

Hygiene:

```powershell
git diff --check
# exit 0

rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
# exit 1, no matches
```

## Novel Progress

本阶段未推进小说正文生成。原因：Phase200 是对话入口 Agent 化的真实写入门禁阶段，目标是让 Agent 可以安全地把 pending action route 迁入 approval-chain。

## Next Phase

建议 Phase201 将该 apply 工具接入对话入口推荐链：

- 当 Phase199 contract preview 返回 `requires_confirmation` 时，在推荐下一步工具中提供 `apply_pending_action_route_approval_opt_in`。
- 对前端/对话投影隐藏 approval hash 明文时仍能保留 Agent 内部工具调用所需参数。
- 验证对话 pending action 从 legacy route 迁入 approval-chain 后，后续确认路径仍按现有 control plane 执行。
