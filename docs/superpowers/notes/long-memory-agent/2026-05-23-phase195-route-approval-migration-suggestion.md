# Phase195 Route Approval Migration Suggestion Report

## Scope

在 route preference projection 中增加 approval-chain opt-in 迁移建议包，让 Agent 能拿到明确、可审计的 route metadata patch，但不执行写入。

## Implementation

- 在 `slash_command_route.py` 新增 `_approval_chain_opt_in_suggestion`。
- `_route_preference` 新增 `approval_chain_opt_in_suggestion` 输出。
- 建议包包含：
  - `status`
  - `param_name`
  - `route_metadata_patch`
  - `expected_prepare_tool_name`
  - `expected_execute_tool_name`
  - `runtime_default_preserved`
  - `guardrails`
- 非 approval-gated route 返回 `None`。
- 未声明 opt-in 且工具可用时返回 `status="available"`。
- 已声明 opt-in 时返回 `status="already_declared"`。
- preferred tools 缺失时返回 `status="blocked_missing_tools"`。

## Behavior

- 默认 setup route 现在能给出：
  - `route_metadata_patch={"use_agent_approval_chain": True}`
  - `expected_prepare_tool_name="prepare_generate_setup_execution"`
  - `expected_execute_tool_name="execute_generate_setup_with_approval"`
- opt-in 模拟 route 的建议状态是 `already_declared`。
- projection 仍只读，不修改 route builder 默认值、pending action 或 dispatch。

## Validation

RED:

```powershell
pytest backend/tests/test_writing_agent_route_preference.py -k "migration_suggestion" -q
# 3 failed, 6 deselected
# failure reason: approval_chain_opt_in_suggestion missing

pytest backend/tests/test_writing_agent_tool_executor.py -k "route_preference_projection and migration_suggestion" -q
# 1 failed, 119 deselected
# failure reason: approval_chain_opt_in_suggestion missing
```

GREEN / T1:

```powershell
pytest backend/tests/test_writing_agent_route_preference.py -k "migration_suggestion" -q
# 3 passed, 6 deselected

pytest backend/tests/test_writing_agent_tool_executor.py -k "route_preference_projection and migration_suggestion" -q
# 1 passed, 119 deselected
```

T2:

```powershell
pytest backend/tests/test_writing_agent_route_preference.py -q
# 9 passed

pytest backend/tests/test_writing_agent_tool_executor.py -k "route_preference_projection" -q
# 4 passed, 116 deselected

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

本阶段未推进小说正文生成。原因：Phase195 仍属于 Agent 路由迁移的可审计规划能力，目标是让 Agent 后续可以做工具化迁移决策。

## Next Phase

建议 Phase196 做一个真正的“写入前计划”工具：给定 pending action 或 route，返回是否可应用 opt-in metadata、所需 patch 和风险提示，但仍不直接写入。
