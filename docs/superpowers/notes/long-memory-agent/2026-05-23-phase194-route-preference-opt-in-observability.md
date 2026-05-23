# Phase194 Route Preference Opt-In Observability Report

## Scope

增强 route preference projection，让 Agent 能看到 approval-chain opt-in metadata 的声明状态，同时默认路由和 dispatch 行为不变。

## Implementation

- `inspect_agent_dialog_route_projection` 新增可选输入 `approval_chain_opt_in_action_types`。
- `inspect_agent_route_preference_projection` 透传该输入，并在 summary/trace 中输出 opt-in 状态。
- `_route_preference` 新增字段：
  - `approval_chain_opt_in_param_name`
  - `approval_chain_opt_in_declared`
  - `approval_chain_opt_in_available`
- 当 route 显式带有 `use_agent_approval_chain=True` 且存在 approval gate 时，`migration_status` 输出 `opt_in_declared`。
- `inspect_agent_route_preference_projection` descriptor 新增 `approval_chain_opt_in_action_types` 输入 schema。
- adapter 透传 `tool.params["approval_chain_opt_in_action_types"]`。

## Behavior

- 默认 projection 仍报告 legacy route 为 `recommended_not_applied`。
- 传入 `approval_chain_opt_in_action_types=["preview_setup"]` 时：
  - setup route 带 `use_agent_approval_chain=True`。
  - setup route 标记 `approval_chain_opt_in_declared=True`。
  - setup route 标记 `migration_status="opt_in_declared"`。
  - summary `opt_in_declared_count=1`。
- projection 只影响报告，不改变真实 pending action route。

## Validation

RED:

```powershell
pytest backend/tests/test_writing_agent_route_preference.py -k "opt_in" -q
# 1 failed, 5 deselected
# failure reason: inspect_agent_route_preference_projection did not accept approval_chain_opt_in_action_types

pytest backend/tests/test_writing_agent_tool_executor.py -k "route_preference_projection and opt_in" -q
# 1 failed, 118 deselected
# failure reason: summary lacked opt_in_declared_count
```

GREEN / T1:

```powershell
pytest backend/tests/test_writing_agent_route_preference.py -k "opt_in" -q
# 1 passed, 5 deselected

pytest backend/tests/test_writing_agent_tool_executor.py -k "route_preference_projection and opt_in" -q
# 1 passed, 118 deselected
```

T2:

```powershell
pytest backend/tests/test_writing_agent_route_preference.py -q
# 6 passed

pytest backend/tests/test_writing_agent_tool_executor.py -k "route_preference_projection" -q
# 3 passed, 116 deselected

pytest backend/tests/test_writing_agent_tool_registry.py -k "route_preference" -q
# 1 passed, 52 deselected

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

本阶段未推进小说正文生成。原因：Phase194 仍处于 Agent 路由迁移基础设施阶段，重点是让 Agent 对 route opt-in 状态具备可观测性。

## Next Phase

建议 Phase195 开始让内部 route preference / control plane 能输出“可执行迁移建议包”，供后续 Agent 决策是否把某条 pending action 写入 opt-in metadata。
