# Phase212 Agent Profile Definition Report

## Scope

把 `agent_profile` 从字符串升级为稳定 profile definition projection，暴露身份、层级和委派边界。

## Plan

见 `docs/superpowers/plans/long-memory-agent/2026-05-24-phase212-agent-profile-definition.md`。

## Reference Project Translation

- OpenHuman：声明式 agent definition 转译为 `agent_profile_definition`。
- Hermes Agent：orchestrator/leaf role 边界转译为 `delegation_allowed`。
- OpenClaw：profile definition 与工具可见性 policy 分离，本阶段不改变执行行为。

## RED

- `pytest backend/tests/test_writing_agent_tool_registry.py -k "agent_profile_tool_projection" -q`
  - 初始失败：`KeyError: 'profile_definitions'`。
- `pytest backend/tests/test_writing_agent_runs.py -k "profile_projection" -q`
  - 初始失败：`KeyError: 'agent_profile_definition'`。
- `npm run test:unit -- AgentRunDrawer`
  - 初始失败：详情抽屉不显示 `编排层级`。

## Implementation

- `agent_tool_surface_policy.py`
  - 新增 `AGENT_PROFILE_DEFINITION_VERSION = "phase212.agent_profile_definition.v1"`。
  - 新增 `AGENT_PROFILE_DEFINITIONS`，定义 `display_name`、`role`、`tier`、`delegation_allowed`、`delegate_to_profiles`。
  - 新增 `build_agent_profile_definitions_projection()` 与 `build_agent_profile_definition()`。
  - `build_agent_profile_tool_projection()` 增加 `profile_definitions`，保持 profile tool policy 和 actual visibility filtering 不变。
- `run_service.py`
  - `detail_payload()` 通过 `_agent_profile_projection()` 暴露 `agent_profile_definition`。
  - profile 来源分为 `planner`、`planner_trace`、`run_input_tools`、`describe_agent_tools_input`。
- `AgentRunDrawer.vue`
  - 优先使用 `agent_profile_definition.display_name` 展示身份。
  - 增加 `编排层级` 与 `委派` 展示。

## Validation

- `pytest backend/tests/test_writing_agent_tool_registry.py -k "agent_profile_tool_projection" -q`
  - 1 passed, 62 deselected.
- `pytest backend/tests/test_writing_agent_runs.py -k "profile_projection" -q`
  - 1 passed, 175 deselected.
- `npm run test:unit -- AgentRunDrawer`
  - 9 passed.
- `pytest backend/tests/test_writing_agent_runs.py -k "profile_projection or auto_plan" -q`
  - 14 passed, 162 deselected.
- `python -m compileall backend/app/services/writing_agent`
  - passed.
- `npm run build`
  - `vue-tsc --noEmit && vite build` passed.
- `git diff --check`
  - passed；仅提示 `backend/tests/test_writing_agent_runs.py` 将从 CRLF 转 LF。
- DeepSeek key prefix scan
  - no matches in `backend frontend docs`.

## Review

- 本地审查：
  - 本阶段只新增 profile definition 投影，不改变 profile scope filtering、planner 选工具、executor 或审批行为。
  - `orchestrator` 的 `delegation_allowed=True` 与 `delegate_to_profiles` 是编排契约表达，不会自动启用委派工具。
  - worker profile 均为 `delegation_allowed=False`，符合 Hermes leaf worker 与 OpenHuman worker 不再挂 subagents 的边界思想。
  - 未复制外部项目框架，只转译 profile metadata 和可观测字段。

## Novel Progress

本阶段不推进正文生成。原因：当前阶段继续打 Agent 编排契约基础，使后续真实长篇生成中的 profile/worker 边界可验证。

## Next

- Phase213 建议把 profile definition 接入 dialog `action_result_view` detail items，或进一步用于 planner trace，使对话消息也能看到 `role/tier/delegation_allowed`。
