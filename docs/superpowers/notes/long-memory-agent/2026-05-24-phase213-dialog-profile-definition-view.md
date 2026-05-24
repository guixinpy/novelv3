# Phase213 Dialog Profile Definition View Report

## Scope

把 `agent_profile_definition` 接入对话 `action_result_view.detail_items` 与前端 fallback projection，显示 Agent 角色、层级和委派边界。

## Plan

见 `docs/superpowers/plans/long-memory-agent/2026-05-24-phase213-dialog-profile-definition-view.md`。

## Reference Project Translation

- OpenHuman：agent definition 的 tier/subagents 转译为对话层 `编排层级` 与 `委派`。
- Hermes Agent：orchestrator/leaf role 边界转译为 `Agent 角色` 与 `委派`。
- OpenClaw：继续只展示结构化摘要，不输出完整工具 schema。

## RED

- `pytest backend/tests/test_dialogs.py -k "agent_discovery_view" -q`
  - 初始失败：`Agent 角色` 不在 `detail_items` 中。
- `npm run test:unit -- agentRunProjection`
  - 初始失败 2 项：
    - recovery preview fallback 不包含 `Agent 角色`。
    - recovery execution feedback 不包含 `Agent 角色`。

## Implementation

- 后端 `action_result_view.py`
  - `_agent_discovery_detail_items()` 读取 `agent_profile_definition`。
  - `Agent 身份` 优先使用 definition 的 `display_name`。
  - 新增 `Agent 角色`、`编排层级`、`委派` detail items。
  - 委派仅展示 `可委派` / `不可委派`，不展示按钮、执行态 run id 或子任务状态。
- 前端 `agentRunProjection.ts`
  - `agentDiscoveryDetailItems()` 读取 `agent_profile_definition`。
  - recovery preview fallback 和 recovery execution feedback 都能展示 role/tier/delegation。

## Validation

- `pytest backend/tests/test_dialogs.py -k "agent_discovery_view" -q`
  - 1 passed, 93 deselected.
- `npm run test:unit -- agentRunProjection`
  - 34 passed.
- `pytest backend/tests/test_dialogs.py -k "agent_discovery_view or action_result_view or agent_run" -q`
  - 5 passed, 89 deselected.
- `python -m compileall backend/app/services/actions`
  - passed.
- `npm run build`
  - `vue-tsc --noEmit && vite build` passed.
- `git diff --check`
  - passed.
- DeepSeek key prefix scan
  - no matches in `backend frontend docs`.

## Review

- 子代理只读参考项目复核：
  - OpenClaw `docs/tools/subagents.md` 采用 compact summary，不展开子会话细节；本阶段只展示 profile 摘要。
  - Hermes `tools/delegate_tool.py` 区分 `leaf/orchestrator`，但本阶段不引入 depth、kill switch 或 auto approve/deny。
  - OpenHuman `definition.rs` 分离 `tools` 与 `subagents`，本阶段避免把 `delegate_to_profiles` 渲染成当前可执行工具。
  - 风险判断：只展示摘要风险可控，但需避免让用户误以为已经有执行层委派 enforcement。
- 本地审查：
  - 只改后端 action result view 和前端 fallback projection，不改 action result 原始业务语义、planner、executor、任务队列或审批行为。
  - 旧 payload 缺少 `agent_profile_definition` 时仍保留原展示。

## Novel Progress

本阶段不推进正文生成。原因：当前阶段继续完善 Agent 运行可观测性，使后续真实创作压测时可直接从对话消息判断当前 worker 的职责边界。

## Next

- Phase214 建议把 `delegate_to_profiles` 作为声明式摘要接入 run drawer 或 dialog view，但需要明确标注为“可委派目标声明”，不能暗示真实子代理执行已经启用。
