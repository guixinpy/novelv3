# Phase199 Route Opt-In Apply Approval Contract Report

## Summary

新增内部只读工具 `preview_pending_action_route_approval_opt_in_apply_contract`，用于基于 Phase198 的 pending action route opt-in apply preview 生成确认前审批契约。

核心行为：

- ready 且存在 `params_diff` 时返回 `status="requires_confirmation"`、`required_confirmation=True`、`approval_contract_hash` 和 `approval_contract`。
- blocked preview 保持 blocked，不生成确认 hash。
- already-declared/no-diff preview 返回 `status="not_required"`。
- 哈希输入是窄 canonical payload，不包含 trace、完整 params、UI 文案、时间戳或 DB 对象引用。
- 工具仍是 read-only preflight，不执行真实 mutation。

## Files Changed

- `backend/app/services/writing_agent/slash_command_route.py`
  - Added `PENDING_ACTION_ROUTE_OPT_IN_APPLY_CONTRACT_VERSION`.
  - Added `build_pending_action_route_approval_opt_in_apply_contract`.
  - Added canonical route opt-in contract hash helper.
- `backend/app/services/writing_agent/agent_core_tool_adapters.py`
  - Added adapter `preview_pending_action_route_approval_opt_in_apply_contract`.
  - Reuses Phase198 preview and blocks non-pending pending actions.
- `backend/app/services/writing_agent/agent_core_tool_descriptors.py`
  - Added descriptor with `target_type="agent_route_approval_opt_in_apply_contract"`.
- `backend/tests/test_writing_agent_tool_executor.py`
  - Added RED/GREEN executor, pure hash stability, blocked/noop, foreign-project leakage, static adapter, metadata, and unhandled-tool tests.
- `backend/tests/test_writing_agent_tool_registry.py`
  - Added descriptor registry test.

## Subagent Review

Explorer `019e5462-c6ae-7fd3-a76e-1f4ae9a84ed1` did a read-only review and recommended:

- Keep this as an internal read-only preflight tool.
- Hash only a narrow stable payload.
- Exclude volatile fields such as trace, full params snapshots, timestamps, UI text, and DB object references.
- Treat already-declared route opt-in as no-op.
- Future real apply must recompute preview and contract before accepting caller-provided hash.

Reviewer `019e546d-8144-7171-814a-c60817174f7c` found one Important issue:

- The contract adapter checked `pending.status != "pending"` before dialog/project scope validation, which could leak foreign-project non-pending params.
- Fixed by validating dialog/project ownership before non-pending status handling.
- Added regression test `test_tool_executor_hides_foreign_non_pending_route_opt_in_apply_contract_params`.

## Validation

RED:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "route_opt_in_apply_contract" -q
# 6 failed, 130 deselected
# failure reasons: tool unhandled; pure builder import missing; adapter metadata missing

pytest backend/tests/test_writing_agent_tool_registry.py -k "route_opt_in_apply_contract" -q
# 1 failed, 55 deselected
# failure reason: descriptor missing
```

GREEN / T1:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "route_opt_in_apply_contract" -q
# 7 passed, 130 deselected

pytest backend/tests/test_writing_agent_tool_registry.py -k "route_opt_in_apply_contract" -q
# 1 passed, 55 deselected
```

T2:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "route_opt_in_apply_contract or route_opt_in_apply or pending_action_route_opt_in_plan or route_approval_opt_in_plan or static_adapter_names or unhandled_internal or agent_core_tool_adapters" -q
# 20 passed, 117 deselected

pytest backend/tests/test_writing_agent_tool_registry.py -k "route_opt_in_apply_contract or route_opt_in_apply_preview or route_approval_opt_in_plan or agent_core_tool_descriptors" -q
# 4 passed, 52 deselected

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

本阶段未推进小说正文生成。原因：Phase199 是对话入口 Agent 化的 guarded-write 基础设施阶段，目标是为后续真实 route opt-in mutation 提供确认门。

## Next Phase

建议 Phase200 实现真实 `apply_pending_action_route_approval_opt_in` mutation 工具：

- 输入必须包含 `confirm_apply=True`、`approval_contract_hash`、`approval_contract`。
- 执行前重新计算 Phase198 preview + Phase199 contract。
- 只有 hash 和 snapshot 都匹配时才更新 `PendingAction.params.agent_route`。
- 写入后返回 params diff、approval verification 和 runtime behavior 说明。
