# Phase196 Route Approval Opt-In Prewrite Plan Report

## Scope

新增只读工具 `plan_agent_route_approval_opt_in`，用于在真正修改 pending action 或 route metadata 前生成可审计的 approval-chain opt-in patch 计划。

## Implementation

- 在 `slash_command_route.py` 新增：
  - `ROUTE_APPROVAL_OPT_IN_PLAN_VERSION`
  - `plan_agent_route_approval_opt_in`
  - `_route_from_plan_input`
  - `_prewrite_plan_status`
- 计划函数支持两类输入：
  - 直接传入 `agent_route`
  - 传入 `action_type/source/command_name` 后临时构造 route。
- 计划函数复用 `_route_preference` 和 Phase195 的 `approval_chain_opt_in_suggestion`。
- 输出始终保持 `write_performed=False`，只返回 patch 和 route_after。
- 输出新增 `risk`：
  - `codes`
  - `missing_preferred_tools`
  - `guardrails`
- 新增 Agent 工具 descriptor / adapter：
  - `plan_agent_route_approval_opt_in`
  - `target_type="agent_route_approval_opt_in_plan"`
  - `category="preflight"`
  - `non_blocking_report=True`
- 修正 `inspect_agent_route_preference_projection` descriptor，补上 `approval_chain_opt_in_action_types` 输入 schema。

## Behavior

- 默认 setup route:
  - `status="ready"`
  - `can_apply=True`
  - `metadata_patch={"use_agent_approval_chain": True}`
  - `route_after.use_agent_approval_chain=True`
- 已声明 opt-in route:
  - `status="already_declared"`
  - `can_apply=False`
  - `risk.codes=["already_declared"]`
- preferred prepare/execute 工具缺失：
  - `status="blocked"`
  - `can_apply=False`
  - `risk.codes=["missing_preferred_tools"]`
- 非 approval-gated route:
  - `status="noop"`
  - `metadata_patch={}`
  - `risk.codes=["approval_gate_not_required"]`
- 若传入 runtime action type 如 `generate_setup` 且没有 route context：
  - `status="noop"`
  - `risk.codes=["action_type_not_dialog_route", "approval_gate_not_required"]`

## Subagent Review

Explorer `019e5449-b8ae-7e43-b008-8c1d8c86324b` 做了只读接入点审查，建议：

- 工具名沿用 `plan_agent_route_approval_opt_in`。
- `target_type` 使用 `agent_route_approval_opt_in_plan`。
- 接入点保持在 `slash_command_route.py`、`agent_core_tool_descriptors.py`、`agent_core_tool_adapters.py`。
- 输出应包含 `risk`，用于标记缺失工具或传入 runtime action type 的误用风险。
- Phase196 不应改 `test_dialogs.py`，因为本阶段不改变 pending action 创建或 dispatch。

## Validation

RED:

```powershell
pytest backend/tests/test_writing_agent_route_preference.py -k "prewrite_plan" -q
# import error: plan_agent_route_approval_opt_in missing

pytest backend/tests/test_writing_agent_tool_registry.py -k "route_preference_projection or route_approval_opt_in_plan" -q
# 2 failed: descriptor schema missing approval_chain_opt_in_action_types; new descriptor missing

pytest backend/tests/test_writing_agent_tool_executor.py -k "route_approval_opt_in_plan" -q
# 2 failed: tool unhandled; adapter metadata missing
```

GREEN / T1:

```powershell
pytest backend/tests/test_writing_agent_route_preference.py -k "prewrite_plan" -q
# 4 passed, 9 deselected

pytest backend/tests/test_writing_agent_tool_registry.py -k "route_preference_projection or route_approval_opt_in_plan" -q
# 2 passed, 52 deselected

pytest backend/tests/test_writing_agent_tool_executor.py -k "route_approval_opt_in_plan" -q
# 2 passed, 120 deselected

pytest backend/tests/test_writing_agent_route_preference.py -k "prewrite_plan" -q
# 5 passed, 9 deselected

pytest backend/tests/test_writing_agent_tool_registry.py -k "agent_core_tool_descriptors or route_approval_opt_in_plan" -q
# 2 passed, 52 deselected

pytest backend/tests/test_writing_agent_tool_executor.py -k "route_approval_opt_in_plan or unhandled_internal" -q
# 3 passed, 119 deselected
```

T2:

```powershell
pytest backend/tests/test_writing_agent_route_preference.py -q
# 14 passed

pytest backend/tests/test_writing_agent_tool_registry.py -k "route_preference_projection or route_approval_opt_in_plan or agent_core_tool_descriptors" -q
# 3 passed, 51 deselected

pytest backend/tests/test_writing_agent_tool_executor.py -k "route_preference_projection or route_approval_opt_in_plan or unhandled_internal or agent_core_tool_adapters" -q
# 8 passed, 114 deselected

pytest backend/tests/test_writing_agent_tool_executor.py -k "static_adapter_names or route_approval_opt_in_plan or unhandled_internal or agent_core_tool_adapters" -q
# 5 passed, 117 deselected

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

本阶段未推进小说正文生成。原因：Phase196 继续处理 Agent 化基础设施，让对话入口迁移具备“先计划、再审批、再执行”的工具化能力。

## Next Phase

建议 Phase197 将 prewrite plan 与真实 pending action 读取连接起来：允许工具按 `pending_action_id` 读取现有 `agent_route` 并返回 patch 计划，但仍不写入。

## Git

- Main commit: `197e3ac9 feat: plan route approval opt in patches`
- Remote: pushed to `origin/main`
