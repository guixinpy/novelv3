# Phase197 Pending Action Route Opt-In Plan Report

## Scope

将 `plan_agent_route_approval_opt_in` 接入真实 `pending_action_id`，让 Agent 能读取待确认操作的 route metadata 并生成只读 opt-in patch 计划。

## Implementation

- `plan_agent_route_approval_opt_in` descriptor 新增 `pending_action_id` 输入字段。
- `_plan_agent_route_approval_opt_in` adapter 支持：
  - 按 `pending_action_id` 查询 `PendingAction`。
  - 校验 pending action 所属 dialog 与当前 project 一致。
  - 从 `pending.params["agent_route"]` 读取真实 route。
  - 复用 Phase196 的 `plan_agent_route_approval_opt_in` 纯函数生成计划。
- 输出 trace 新增：
  - `pending_action_id`
  - `pending_action_type`
  - `pending_action_route_source="pending_action"`
- 缺失 pending action 时返回 blocked plan：
  - `status="blocked"`
  - `can_apply=False`
  - `risk.codes=["pending_action_not_found"]`
- 不写入 `PendingAction.params`。

## Behavior

- 给定真实 pending action id：
  - 输出 `status="ready"`。
  - 输出 `metadata_patch={"use_agent_approval_chain": True}`。
  - `write_performed=False`。
  - 数据库中的 pending params 保持原样。
- 给定不存在的 pending action id：
  - 输出 `status="blocked"`。
  - 输出 `risk.codes=["pending_action_not_found"]`。

## Validation

RED:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "pending_action_route_opt_in_plan" -q
# 2 failed, 122 deselected
# failure reasons: adapter ignored pending_action_id; missing id returned route_not_available

pytest backend/tests/test_writing_agent_tool_registry.py -k "route_approval_opt_in_plan" -q
# 1 failed, 53 deselected
# failure reason: descriptor lacked pending_action_id
```

GREEN / T1:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "pending_action_route_opt_in_plan" -q
# 2 passed, 122 deselected

pytest backend/tests/test_writing_agent_tool_registry.py -k "route_approval_opt_in_plan" -q
# 1 passed, 53 deselected
```

T2:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "pending_action_route_opt_in_plan or route_approval_opt_in_plan" -q
# 4 passed, 120 deselected

pytest backend/tests/test_writing_agent_tool_registry.py -k "route_approval_opt_in_plan" -q
# 1 passed, 53 deselected

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

本阶段未推进小说正文生成。原因：Phase197 仍属于对话入口 Agent 化基础设施，目标是让 Agent 能从真实 pending action 读取 route 并形成写入前计划。

## Next Phase

建议 Phase198 实现只读 apply-preview：给定 pending action id 和 prewrite plan，返回“如果执行写入会产生的 pending params diff”，仍不真正写入。
