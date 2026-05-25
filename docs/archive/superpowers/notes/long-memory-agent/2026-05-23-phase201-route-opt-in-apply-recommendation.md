# Phase201 Route Opt-In Apply Recommendation Report

## Scope

将 Phase199/200 的 pending action route opt-in contract/apply 链路接入 Agent 推荐后继链：

- contract preview 在需要确认时推荐 guarded apply 工具；
- recommended follow-up planner 可安全规划 contract preview，并携带 `pending_action_id`；
- guarded apply 仍不进入自动执行后继；
- 普通前端 fallback view 不显示审批 hash、完整 contract 或 route diff。

## Plan

见 `docs/superpowers/plans/long-memory-agent/2026-05-23-phase201-route-opt-in-apply-recommendation.md`。

## RED

- `pytest backend/tests/test_writing_agent_tool_executor.py -k "recommended_followups or route_opt_in_apply_contract" -q`
  - 结果：`5 failed, 8 passed, 137 deselected`
  - 预期失败：
    - contract preview 缺少 `recommended_next_tools` / `recommended_next_tool_calls`；
    - recommended follow-up planner 未把 `preview_pending_action_route_approval_opt_in_apply_contract` 视为安全后继。
- `npm --prefix frontend run test:unit -- agentRunProjection`
  - 结果：`4 failed, 30 passed`
  - 预期失败：前端不识别 route opt-in contract/apply action type，fallback view 为 `null`。
- 备注：第一次使用 `npm --prefix frontend run test -- agentRunProjection` 失败，因为项目脚本名是 `test:unit`，不是 `test`。

## Implementation

- `slash_command_route.py`
  - `_route_opt_in_contract_output` 在 `status="requires_confirmation"` 时输出：
    - `recommended_next_tools: ["apply_pending_action_route_approval_opt_in"]`
    - `recommended_next_tool_calls`，包含 Agent 内部 apply 调用参数、`confirm_apply=True`、审批 hash 和 contract。
  - blocked / not_required 输出空推荐，避免误导 planner。
- `recommended_followup_planner.py`
  - 将 `preview_pending_action_route_approval_opt_in_apply_contract` 加入安全后继列表。
  - 未将 `apply_pending_action_route_approval_opt_in` 加入安全列表，保持 guarded apply 不能被自动执行。
  - 新增 pending action id 提取逻辑，从 source step 输出、`agent_tool_result.output`、输入 params 中寻找 `pending_action_id`。
- `agent_core_tool_descriptors.py`
  - contract preview 输出 schema 补充推荐字段。
- `agentRunProjection.ts`
  - 新增 route opt-in contract/apply fallback view。
  - 只显示状态、确认需求、风险数量、写入结果、原因、副作用数量和下一步数量，不显示 hash、完整 contract、route diff 或 params。

## Validation

- GREEN:
  - `pytest backend/tests/test_writing_agent_tool_executor.py -k "recommended_followups or route_opt_in_apply_contract" -q`
    - `13 passed, 137 deselected`
  - `npm --prefix frontend run test:unit -- agentRunProjection`
    - `34 passed`
- T2:
  - `pytest backend/tests/test_writing_agent_tool_executor.py -k "recommended_followups or route_opt_in_apply_contract or apply_route_opt_in" -q`
    - `24 passed, 126 deselected`
  - `pytest backend/tests/test_writing_agent_tool_registry.py -k "route_opt_in_apply or recommended_followups" -q`
    - `2 passed, 55 deselected`
  - `pytest backend/tests/test_writing_agent_runs.py -k "recommended_followup" -q`
    - `6 passed, 169 deselected`
  - `npm --prefix frontend run test:unit -- agentRunProjection`
    - `34 passed`
  - `python -m compileall backend/app/services/writing_agent`
    - exit 0
  - `npm --prefix frontend run build`
    - `vue-tsc --noEmit && vite build` exit 0
  - `git diff --check`
    - exit 0
  - 真实 DeepSeek key 前缀扫描
    - exit 1，无真实 DeepSeek key 片段命中
  - `rg -n "sk-[A-Za-z0-9]{8,}" .`
    - 仅命中既有测试 fixture 中的假 key 字符串和普通 `task-...` 文本。

## Review

- 子代理审查 `019e54aa-5f19-7ee2-b577-7f498c4eff01`：
  - Critical：无。
  - Important：无。
  - Minor：无。
  - 核对结论：
    - apply 仍然 guarded，未加入 `SAFE_RECOMMENDED_FOLLOWUP_TOOLS`；
    - safe follow-up 只生成 contract preview，params 为 `{"pending_action_id": pending.id}`；
    - 前端 view 不包含 approval hash、完整 contract、route diff 或 params；
    - 测试覆盖 contract 推荐、planner 安全边界和前端脱敏。

## Next

- Phase202 建议：把对话入口在 pending action 场景下的 Agent 推荐说明进一步投影到用户可见的安全提示中，例如“可先生成路由升级审批契约”，但仍不直接暴露内部 hash/contract，也不绕过 `resolve-action` 确认。
