# Phase198 Pending Action Route Opt-In Apply Preview Report

## Scope

新增只读 Agent 工具 `preview_pending_action_route_approval_opt_in_apply`，用于预览对真实 `PendingAction.params` 应用 route approval opt-in patch 后的 diff。

## Implementation

- 在 `slash_command_route.py` 新增：
  - `PENDING_ACTION_ROUTE_OPT_IN_APPLY_PREVIEW_VERSION`
  - `preview_pending_action_route_approval_opt_in_apply`
- 纯函数输入：
  - `pending_action_id`
  - `pending_action_type`
  - `pending_params`
  - `route_plan`
- 纯函数输出：
  - `params_before`
  - `params_after`
  - `params_diff`
  - `route_plan`
  - `risk`
  - `write_performed=False`
- 使用 `copy.deepcopy` 构造 `params_before` / `params_after`，避免嵌套 `agent_route` 引用污染 ORM JSON 对象。
- 在 `agent_core_tool_adapters.py` 新增 adapter：
  - 按 `pending_action_id` 查询 `PendingAction` 和 `Dialog`
  - 校验 project ownership
  - 缺失 `params.agent_route` 时返回 `pending_action_agent_route_missing`
  - 顶层 `params.use_agent_approval_chain is False` 时返回 `pending_action_top_level_override`
  - 复用 `plan_agent_route_approval_opt_in`
  - 调用 apply-preview 纯函数
- 在 `agent_core_tool_descriptors.py` 新增 descriptor：
  - `target_type="agent_route_approval_opt_in_apply_preview"`
  - internal/preflight/non-blocking

## Behavior

- legacy route pending action:
  - `status="ready"`
  - `params_diff["agent_route"]` 展示 before/after
  - `params_after["agent_route"]["use_agent_approval_chain"] is True`
  - 数据库 `PendingAction.params` 不变
- already-declared route:
  - `status="already_declared"`
  - `params_diff={}`
  - `params_after == params_before`
- missing pending action:
  - `status="blocked"`
  - `risk.codes=["pending_action_not_found"]`
  - `params_diff={}`
- missing pending action route:
  - `status="blocked"`
  - `risk.codes=["pending_action_agent_route_missing"]`
  - 不合成 route
- top-level override:
  - `status="blocked"`
  - `risk.codes=["pending_action_top_level_override"]`
  - 不输出 nested route diff

## Subagent Review

Explorer `019e5457-6950-71a2-b48a-346e90e4b44f` 做了只读接入点审查，建议：

- 工具名使用 `preview_pending_action_route_approval_opt_in_apply`，明确只读预览。
- `target_type` 使用 `agent_route_approval_opt_in_apply_preview`。
- 纯函数放在 `slash_command_route.py`，adapter 负责 DB 查询。
- 使用 deep copy，避免 nested JSON 引用污染。
- 缺失 `params.agent_route` 时不要凭空合成 route。
- 顶层 `use_agent_approval_chain=False` 会覆盖 nested route patch，必须显式暴露风险。

## Validation

RED:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "route_opt_in_apply_preview" -q
# 2 failed, 126 deselected
# failure reasons: tool unhandled; adapter metadata missing

pytest backend/tests/test_writing_agent_tool_registry.py -k "route_opt_in_apply_preview" -q
# 1 failed, 54 deselected
# failure reason: descriptor missing
```

GREEN / T1:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "route_opt_in_apply" -q
# 6 passed, 124 deselected

pytest backend/tests/test_writing_agent_tool_registry.py -k "route_opt_in_apply_preview" -q
# 1 passed, 54 deselected
```

T2:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "route_opt_in_apply or pending_action_route_opt_in_plan or route_approval_opt_in_plan or static_adapter_names or unhandled_internal or agent_core_tool_adapters" -q
# 13 passed, 117 deselected

pytest backend/tests/test_writing_agent_tool_registry.py -k "route_opt_in_apply_preview or route_approval_opt_in_plan or agent_core_tool_descriptors" -q
# 3 passed, 52 deselected

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

本阶段未推进小说正文生成。原因：Phase198 仍是对话入口 Agent 化的 write-gate 基础设施阶段，目标是让 Agent 在写入前能审计 params diff。

## Next Phase

建议 Phase199 增加真实 apply 工具的审批契约预览：在不写入的情况下生成 `approval_contract_hash`，为后续真正 mutation 工具提供确认门。

## Git

- Main commit: `055b36a6 feat: preview pending route opt in apply`
- Remote: pushed to `origin/main`
