# Phase211 Dialog Agent Discovery View Report

## Scope

让对话消息的 `action_result_view.detail_items` 显示 Agent 身份与 profile-scoped tool discovery 摘要。

## Plan

见 `docs/superpowers/plans/long-memory-agent/2026-05-24-phase211-dialog-agent-discovery-view.md`。

## Reference Project Translation

- OpenClaw：把有效工具面摘要投影为结构化 event details，本阶段转译为对话 detail items。
- Hermes Agent：profile 是运行上下文的一部分，本阶段让对话消息也能显示 profile。
- OpenHuman：agent identity 与 visible tools 分离，本阶段在同一个 action result view 中同时显示身份和工具面。

## RED

- `pytest backend/tests/test_dialogs.py -k "agent_discovery_view" -q`
  - 初始失败：`KeyError: 'detail_items'`，server-side `action_result_view` 未读取 Agent discovery 字段。
- `npm run test:unit -- agentRunProjection`
  - 初始失败 2 项：
    - recovery preview fallback 不包含 `Agent 身份` 等 detail items。
    - recovery execution feedback 不包含 `Agent 身份` 等 detail items。

## Implementation

- 后端 `action_result_view.py`
  - 新增 `_agent_discovery_detail_items()`。
  - 新增 profile/status 中文标签 helper。
  - `plan_recovery_tools` detail items 追加 Agent 身份、工具面、可见工具、已过滤。
  - 普通 action result 若有 `agent_profile` / `agent_tool_discovery`，即使没有 approval decision，也会生成 detail items。
- 前端 `agentRunProjection.ts`
  - 新增 `agentDiscoveryDetailItems()`。
  - recovery preview fallback 追加 Agent discovery detail items。
  - recovery execution feedback 追加 Agent discovery detail items。
  - recovery execution fallback 支持从 `action_result.data` 中读取 Agent discovery detail items。

## Validation

- `pytest backend/tests/test_dialogs.py -k "agent_discovery_view" -q`
  - 1 passed, 93 deselected.
- `npm run test:unit -- agentRunProjection`
  - 34 passed.
- `pytest backend/tests/test_dialogs.py -k "agent_discovery_view or action_result_view or agent_run" -q`
  - 5 passed, 89 deselected.
- `python -m compileall backend/app/services/actions backend/app/services/writing_agent`
  - passed.
- `npm run build`
  - `vue-tsc --noEmit && vite build` passed.
- `git diff --check`
  - passed.
- DeepSeek key prefix scan
  - no matches in `backend frontend docs`.

## Review

- 本地审查：
  - 该阶段只改 action result view / frontend fallback projection，不改 action result 原始数据、不改 run execution、不改 planner/tool policy。
  - 旧 payload 没有 `agent_profile` / `agent_tool_discovery` 时不会新增 detail items，保持原显示。
  - 只展示摘要计数和中文状态，不泄露工具全量 schema、approval hash 或内部契约。

## Novel Progress

本阶段不推进正文生成。原因：当前阶段继续完善 Agent 编排可观测性，降低后续长篇生成压测时定位工具面错误的成本。

## Next

- Phase212 建议把 `agent_profile` 进一步正式化为 profile definition projection，补 `role/source/tier/delegation_allowed`，对应 OpenHuman 的声明式 agent definition 与 Hermes subagent role 边界。
