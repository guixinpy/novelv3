# Phase214 Delegate Profile Targets View Report

## Scope

把 `agent_profile_definition.delegate_to_profiles` 作为声明型摘要展示到：

- 后端对话 `action_result_view.detail_items`
- 前端 `agentRunProjection` fallback view
- `AgentRunDrawer` 运行详情抽屉

展示文案统一为 `可委派目标: N 个声明`。该信息只表示 profile 声明，不表示当前 runtime 已执行委派。

## Plan

见 `docs/superpowers/plans/long-memory-agent/2026-05-24-phase214-delegate-profile-targets-view.md`。

## Reference Project Translation

- Hermes Agent：`delegate_task` 明确区分 `leaf/orchestrator`，并有 depth/concurrency/orchestrator enablement 等运行时边界。本阶段只学习其“委派能力必须可观察”的部分，不引入 runtime delegation。
- OpenHuman：agent definition 中 tools/subagents 是能力面声明。本阶段把 `delegate_to_profiles` 作为 profile declaration 计数展示。
- OpenClaw：subagent/tool inventory 以 compact metadata 暴露。本阶段继续只展示摘要计数，不展开完整 schema，不提供执行入口。

## RED

- `pytest backend/tests/test_dialogs.py -k "delegate_profile_targets" -q`
  - 初始失败：`detail_items` 缺少 `{"label": "可委派目标", "value": "4 个声明"}`。
- `npm run test:unit -- agentRunProjection`（工作目录 `frontend/`）
  - 初始失败 1 项：fallback view 缺少 `可委派目标`。
- `npm run test:unit -- AgentRunDrawer`（工作目录 `frontend/`）
  - 初始失败 1 项：运行抽屉缺少 `可委派目标`。

## Implementation

- 后端 `action_result_view.py`
  - 在 `_agent_discovery_detail_items()` 中读取 `delegate_to_profiles`。
  - 仅当 `delegation_allowed is True` 且目标数组非空时展示 `可委派目标`。
- 前端 `agentRunProjection.ts`
  - 在 `agentDiscoveryDetailItems()` 中采用同样条件展示声明计数。
- 前端 `AgentRunDrawer.vue`
  - 新增 `agentProfileDelegateTargetCount`。
  - 仅在 count 大于 0 时渲染 `可委派目标`。
- 测试
  - 后端新增 orchestrator profile projection 用例。
  - 前端新增 fallback projection 用例。
  - 前端新增 drawer orchestrator 用例。

## Validation

- `pytest backend/tests/test_dialogs.py -k "delegate_profile_targets" -q`
  - 1 passed, 94 deselected.
- `npm run test:unit -- agentRunProjection`（工作目录 `frontend/`）
  - 35 passed.
- `npm run test:unit -- AgentRunDrawer`（工作目录 `frontend/`）
  - 10 passed.
- `pytest backend/tests/test_dialogs.py -k "delegate_profile_targets or agent_discovery_view or action_result_view" -q`
  - 4 passed, 91 deselected.
- `python -m compileall backend/app/services/actions`
  - passed.
- `npm run build`（工作目录 `frontend/`）
  - `vue-tsc --noEmit && vite build` passed.
- `git diff --check`
  - passed.
- DeepSeek key prefix scan
  - no matches in `backend frontend docs`.

## Review

- 变更边界保持在 projection / view 层，未改变 planner、executor、tool registry、任务队列或审批行为。
- 文案使用“声明”而不是“可执行目标”，避免让用户误解 runtime delegation 已经落地。
- worker profile 没有 delegate targets 时不显示该字段，避免增加噪音。

## Novel Progress

本阶段不推进正文生成。原因：当前阶段继续补 Agent 编排可观测性，后续长篇压力测试需要先能从运行详情判断当前 profile 的委派边界。

## Next

- 继续吸收 Hermes/OpenHuman/OpenClaw 的 Agent 工程：下一阶段建议把 `delegate_to_profiles` 与工具注册表的 profile policy 做一致性检查，先输出审计报告，不直接启用子代理 runtime。
